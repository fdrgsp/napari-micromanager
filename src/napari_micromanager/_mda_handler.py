from __future__ import annotations

import contextlib
import tempfile
import time
from typing import TYPE_CHECKING, Any, Callable, Deque, Generator, cast

import napari
import numpy as np
import zarr
from pymmcore_plus import CMMCorePlus
from superqt.utils import create_worker, ensure_main_thread
from tqdm import tqdm
from useq import MDAEvent, MDASequence

from ._mda_meta import SEQUENCE_META_KEY, SequenceMeta

if TYPE_CHECKING:
    from uuid import UUID

    import napari.viewer
    from napari.layers import Image
    from pymmcore_plus.core.events._protocol import PSignalInstance
    from typing_extensions import NotRequired, TypedDict

    class SequenceMetaDict(TypedDict):
        """Dict containing the SequenceMeta object that we add when starting MDAs."""

        napari_mm_sequence_meta: SequenceMeta

    class ActiveMDASequence(MDASequence):
        """MDASequence that whose metadata dict contains our special SequenceMeta."""

        metadata: SequenceMetaDict  # type: ignore [assignment]

    class ActiveMDAEvent(MDAEvent):
        """Event that has been assigned a sequence."""

        sequence: ActiveMDASequence

    # TODO: the keys are accurate, but currently this is at the top level layer.metadata
    # we should nest it under a napari_micromanager key
    class LayerMeta(TypedDict):
        """Metadata that we add to layer.metadata."""

        mode: str
        useq_sequence: MDASequence
        uid: UUID
        grid: NotRequired[str]
        grid_pos: NotRequired[str]
        ch_id: NotRequired[str]
        translate: NotRequired[bool]


class _NapariMDAHandler:
    """Object mediating events between an in-progress MDA and the napari viewer.

    It is typically created by the MainWindow, but could conceivably live alone.

    Parameters
    ----------
    mmcore : CMMCorePlus
        The Micro-Manager core instance.
    viewer : napari.viewer.Viewer
        The napari viewer instance.
    """

    def __init__(self, mmcore: CMMCorePlus, viewer: napari.viewer.Viewer) -> None:
        self._mmc = mmcore
        self.viewer = viewer

        # mapping of id -> (zarr.Array, temporary directory) for each layer created
        self._tmp_arrays: dict[str, tuple[zarr.Array, tempfile.TemporaryDirectory]] = {}
        self._deck: Deque[tuple[np.ndarray, MDAEvent]] = Deque()

        # Add all core connections to this list.  This makes it easy to disconnect
        # from core when this widget is closed.
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self._mmc.mda.events.frameReady, self._on_mda_frame),
            (self._mmc.mda.events.sequenceStarted, self._on_mda_started),
            (self._mmc.mda.events.sequenceFinished, self._on_mda_finished),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

    def _cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        for z, v in self._tmp_arrays.values():
            z.store.close()
            with contextlib.suppress(NotADirectoryError):
                v.cleanup()

    @ensure_main_thread  # type: ignore [misc]
    def _on_mda_started(self, sequence: MDASequence) -> None:
        """Create temp folder and block gui when mda starts."""
        meta: SequenceMeta | None = sequence.metadata.get(SEQUENCE_META_KEY)

        if meta is None:
            # this is not an MDA we started
            # TODO: should we still handle this with some sane defaults?
            return
        sequence = cast("ActiveMDASequence", sequence)

        # pause acquisition until zarr layer(s) are added
        self._mmc.mda.toggle_pause()

        # determine the new layers that need to be created for this experiment
        # (based on the sequence mode, and whether we're splitting C/P, etc.)
        axis_labels, layers_to_create = _determine_sequence_layers(sequence)

        yx_shape = [self._mmc.getImageHeight(), self._mmc.getImageWidth()]

        # now create a zarr array in a temporary directory for each layer
        for id_, shape, kwargs in layers_to_create:
            tmp = tempfile.TemporaryDirectory()
            dtype = f"uint{self._mmc.getImageBitDepth()}"

            # create the zarr array and add it to the viewer
            z = zarr.open(str(tmp.name), shape=shape + yx_shape, dtype=dtype)
            fname = meta.file_name if meta.should_save else "Exp"
            self._create_empty_image_layer(z, f"{fname}_{id_}", sequence, **kwargs)

            # store the zarr array and temporary directory for later cleanup
            self._tmp_arrays[id_] = (z, tmp)

        # set axis_labels after adding the images to ensure that the dims exist
        self.viewer.dims.axis_labels = axis_labels

        # resume acquisition after zarr layer(s) is(are) added
        # FIXME: this isn't in an event loop... so shouldn't we just call toggle_pause?
        for i in self.viewer.layers:
            if i.metadata.get("uid") == sequence.uid:
                self._mmc.mda.toggle_pause()
                break

        # init index will always be less than any event index
        # self._largest_idx: tuple[int, ...] = (-1,)
        self._deck = Deque()
        self._mda_running = True
        self._io_t = create_worker(
            self._watch_mda,
            _start_thread=True,
            _connect={"finished": self._on_io_finished},
        )

    def _watch_mda(self) -> Generator[None, None, None]:
        while self._mda_running:
            if self._deck:
                self._process_frame(*self._deck.pop())
            else:
                time.sleep(0.1)
            yield

    def _on_io_finished(self) -> None:
        # process remaining frames
        with tqdm(
            total=len(self._deck), desc="Processing remaining MDA frames:"
        ) as progress:
            while self._deck:
                self._process_frame(*self._deck.pop())
                progress.update()
            self.viewer.status = ""

    def _on_mda_frame(self, image: np.ndarray, event: MDAEvent) -> None:
        """Called on the `frameReady` event from the core."""
        self._deck.append((image, event))

    def _process_frame(self, image: np.ndarray, event: MDAEvent) -> None:
        seq_meta = getattr(event.sequence, "metadata", None)

        if not (seq_meta and seq_meta.get(SEQUENCE_META_KEY)):
            # this is not an MDA we started
            return
        event = cast("ActiveMDAEvent", event)

        # get info about the layer we need to update
        _id, im_idx, layer_name = _id_idx_layer(event)

        # update the zarr array backing the layer
        self._tmp_arrays[_id][0][im_idx] = image

        self._add_stage_pos_metadata(layer_name, im_idx)

        # if im_idx > self._largest_idx:
        # self._largest_idx = im_idx
        self._update_viewer_dims(layer_name, im_idx)

    @ensure_main_thread  # type: ignore [misc]
    def _update_viewer_dims(self, layer_name: str, im_idx: tuple[int, ...]) -> None:
        cs = list(self.viewer.dims.current_step)
        for a, v in enumerate(im_idx):
            cs[a] = v
        self.viewer.dims.current_step = cs

        # update display
        layer: Image = self.viewer.layers[layer_name]
        if not layer.visible:
            layer.visible = True
        # layer.reset_contrast_limits()

    def _on_mda_finished(self, sequence: MDASequence) -> None:
        self._mda_running = False
        self.viewer.status = "Processing remaining MDA frames..."

    def _add_stage_pos_metadata(self, layer_name: str, image_idx: tuple) -> None:
        """Add positions info to layer metadata.

        This info is used in the `_mouse_right_click` method.
        """
        layer = self.viewer.layers[layer_name]
        x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
        z = self._mmc.getZPosition()
        info = (image_idx, x, y, z)

        try:
            layer.metadata["positions"].append(info)
        except KeyError:
            layer.metadata["positions"] = [info]

    def _create_empty_image_layer(
        self,
        arr: zarr.Array,
        name: str,
        sequence: MDASequence,
        **kwargs: Any,  # extra kwargs to add to layer metadata
    ) -> Image:
        """Create new napari layer for zarr array about to be acquired.

        Parameters
        ----------
        arr : zarr.Array
            The array to create a layer for.
        name : str
            The name of the layer.
        sequence : MDASequence
            The sequence that will be acquired.
        **kwargs
            Extra kwargs will be added to `layer.metadata`.
        """
        # we won't have reached this point if meta is None
        meta = cast("SequenceMeta", sequence.metadata.get(SEQUENCE_META_KEY))

        # add Z to layer scale
        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            scale = [1.0] * (arr.ndim - 2) + [pix_size] * 2
            if (index := sequence.used_axes.find("z")) > -1:
                if meta.split_channels and sequence.used_axes.find("c") < index:
                    index -= 1
                scale[index] = getattr(sequence.z_plan, "step", 1)
        else:
            scale = None

        return self.viewer.add_image(
            arr,
            name=name,
            blending="additive",
            visible=False,
            scale=scale,
            metadata={
                "mode": meta.mode,
                "useq_sequence": sequence,
                "uid": sequence.uid,
                **kwargs,
            },
        )


def _get_axis_labels(sequence: MDASequence) -> tuple[list[str], bool]:
    # sourcery skip: use-next
    main_seq_axis = list(sequence.used_axes)

    if not sequence.stage_positions:
        return main_seq_axis, False

    sub_seq_axis: list | None = None
    for p in sequence.stage_positions:
        if p.sequence:  # type: ignore
            sub_seq_axis = list(p.sequence.used_axes)  # type: ignore
            break

    if sub_seq_axis:
        main_seq_axis.extend(sub_seq_axis)

    return list(set(main_seq_axis)), bool(sub_seq_axis)


def _determine_sequence_layers(
    sequence: ActiveMDASequence,
) -> tuple[list[str], list[tuple[str, list[int], dict[str, Any]]]]:
    # sourcery skip: extract-duplicate-method
    """Return (axis_labels, (id, shape, and metadata)) for each layer to add for seq.

    This function is called at the beginning of a new MDA sequence to determine
    how many layers we're going to create, and what their shapes and metadata
    should be. The data is used to create new empty zarr arrays and napari layers.

    Parameters
    ----------
    sequence : MDASequence
        The sequence to get layers for.
    img_shape : tuple[int, int]
        The YX shape of a single image in the sequence.
        (this argument might not need to be passed here, perhaps could be handled
        be the caller of this function)

    Returns
    -------
    tuple[list[str], list[tuple[str, list[int], dict[str, Any]]]]
        A 2-tuple of `(axis_labels, layer_info)` where:
            - `axis_labels` is a list of axis names.
            e.g. `['t', 'c', 'g', 'z', 'y', 'x']`
            - `layer_info` is a list of `(id, layer_shape, layer_meta)` tuples, where
              `id` is a unique id for the layer, `layer_shape` is the shape of the
              layer, and `layer_meta` is metadata to add to `layer.metadata`. e.g.:
              `[('3670fc63-c570-4920-949f-16601143f2e3', [4, 2, 4], {})]`
    """
    # if we got to this point, sequence.metadata[SEQUENCE_META_KEY] should exist
    meta = sequence.metadata["napari_mm_sequence_meta"]

    # these are all the layers we're going to create
    # each item is a tuple of (id, shape, layer_metadata)
    _layer_info: list[tuple[str, list[int], dict[str, Any]]] = []

    axis_labels, pos_sequence = _get_axis_labels(sequence)

    layer_shape = [sequence.sizes[k] or 1 for k in axis_labels]

    if pos_sequence:
        for p in sequence.stage_positions:
            if not p.sequence:  # type: ignore
                continue
            pos_g_shape = p.sequence.sizes["g"]  # type: ignore
            index = axis_labels.index("g")
            layer_shape[index] = max(layer_shape[index], pos_g_shape)

    if meta.split_channels:
        c_idx = axis_labels.index("c")
        axis_labels.pop(c_idx)
        layer_shape.pop(c_idx)
        for i, ch in enumerate(sequence.channels):
            channel_id = f"{ch.config}_{i:03d}"
            id_ = f"{sequence.uid}_{channel_id}"
            _layer_info.append((id_, layer_shape, {"ch_id": channel_id}))

    else:
        _layer_info.append((str(sequence.uid), layer_shape, {}))

    axis_labels += ["y", "x"]

    return axis_labels, _layer_info


def _id_idx_layer(event: ActiveMDAEvent) -> tuple[str, tuple[int, ...], str]:
    """Get the tmp_path id, index, and layer name for a given event.

    Parameters
    ----------
    event : ActiveMDAEvent
        An event for which to retrieve the id, index, and layer name.


    Returns
    -------
    tuple[str, tuple[int, ...], str]
        A 3-tuple of (id, index, layer_name) where:
            - `id` is the id of the tmp_path for the event (to get the zarr array).
            - `index` is the index in the underlying zarr array where the event image
              should be saved.
            - `layer_name` is the name of the corresponding layer in the viewer.
    """
    meta = cast("SequenceMeta", event.sequence.metadata.get(SEQUENCE_META_KEY))

    axis_order, pos_sequence = _get_axis_labels(event.sequence)

    suffix = ""
    prefix = meta.file_name if meta.should_save else "Exp"

    if meta.split_channels and event.channel:
        suffix = f"_{event.channel.config}_{event.index['c']:03d}"
        axis_order.remove("c")

    _id = f"{event.sequence.uid}{suffix}"

    # the index of this event in the full zarr array
    im_idx: tuple[int, ...] = ()
    for k in axis_order:
        try:
            im_idx += (event.index[k],)
        # if axis not in event.index
        # e.g. if we have bot a position sequence grid and a single position
        except KeyError:
            im_idx += (0,)

    # the name of this layer in the napari viewer
    layer_name = f"{prefix}_{event.sequence.uid}{suffix}"

    return _id, im_idx, layer_name
