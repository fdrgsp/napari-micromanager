import contextlib
from typing import cast
from uuid import UUID

import napari.viewer
import zarr
from numpy import ndarray
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import OMEZarrWriter
from pymmcore_widgets.useq_widgets._mda_sequence import PYMMCW_METADATA_KEY
from useq import MDAEvent, MDASequence

POS_PREFIX = "p"
EXP = "MDA"


class _Handler(OMEZarrWriter):
    def __init__(self, viewer: napari.viewer.Viewer, mmcore: CMMCorePlus | None = None):
        super().__init__()

        self._mmc = mmcore or CMMCorePlus.instance()
        self.viewer = viewer

        # TODO: add the possibility to set either memory or store
        self._group: zarr.Group = zarr.group()
        self._mda_running: bool = False

        self._mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)
        self._mmc.mda.events.frameReady.connect(self.frameReady)
        self._mmc.mda.events.sequenceFinished.connect(self.sequenceFinished)

        self._fname: str = EXP

    def _cleanup(self) -> None:
        with contextlib.suppress(TypeError, RuntimeError):
            self._mmc.mda.events.sequenceStarted.disconnect(self.sequenceStarted)
            self._mmc.mda.events.frameReady.disconnect(self.frameReady)
            self._mmc.mda.events.sequenceFinished.disconnect(self.sequenceFinished)

    def sequenceStarted(self, sequence: MDASequence) -> None:
        """Start the acquisition."""
        self._mda_running = True
        self._reset_group()
        super().sequenceStarted(sequence)

        self._fname = self._get_filename_form_meatdata(sequence)

    def _get_filename_form_meatdata(self, sequence: MDASequence) -> str:
        """Get the filename from the sequence metadata."""
        if meta := cast(dict, sequence.metadata.get(PYMMCW_METADATA_KEY, {})):
            fname = cast(str, meta.get("save_name", ""))
            if fname:
                # remove extension
                fname = fname.rsplit(".", 1)[0]  # ['test.ome', 'tiff']
                if fname.endswith(".ome"):
                    fname = fname.replace(".ome", "") or EXP
            else:
                fname = EXP

            return fname

        return EXP

    def _reset_group(self) -> None:
        """Reset the handler to a clean state."""
        self._group = zarr.group()
        self.position_arrays.clear()

    def frameReady(self, frame: ndarray, event: MDAEvent, meta: dict) -> None:
        """Update the viewer with the current acquisition."""
        if not self.current_sequence:
            return

        super().frameReady(frame, event, meta)

        p_index = event.index.get("p", 0)
        key = f"{POS_PREFIX}{p_index}"
        layer_name = f"{self._fname}_{key}"

        if not self.position_arrays:
            return

        # get all layers with sequence uid metadata
        layers_meta = self._get_layers_mets()

        # if the current sequence uid is not in the layers metadata, add the image
        if (self.current_sequence.uid, key) not in layers_meta:
            self.viewer.add_image(
                self.position_arrays[key],
                name=layer_name,
                blending="opaque",  # self._get_layer_blending().fix for split channels
                metadata={"sequence_uid": self.current_sequence.uid, "key": key},
                scale=self._get_scale(key),
            )
            self.viewer.dims.axis_labels = self.position_arrays[key].attrs[
                "_ARRAY_DIMENSIONS"
            ]

        # update the slider position
        elif self._mda_running:
            self._update_sliders_position(event, p_index)

    def _get_layers_mets(self) -> list[tuple[UUID, str]]:
        """Get the list of uids from the layers metadata."""
        return [
            (layer.metadata.get("sequence_uid"), layer.metadata.get("key"))
            for layer in self.viewer.layers
            if layer.metadata.get("sequence_uid") is not None
            and layer.metadata.get("key") is not None
        ]

    def _update_sliders_position(self, event: MDAEvent, p_index: int) -> None:
        """Update the sliders position."""
        cs = list(self.viewer.dims.current_step)
        index = tuple(event.index[k] for k in self.position_sizes[p_index])
        for a, v in enumerate(index):
            cs[a] = v
        self.viewer.dims.current_step = cs

    def _get_scale(self, fname: str) -> list[float]:
        """Get the scale for the layer."""
        if self.current_sequence is None:
            raise ValueError("Not a MDA sequence.")

        # add Z to layer scale
        arr = self.position_arrays[fname]
        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            scale = [1.0] * (arr.ndim - 2) + [pix_size] * 2
            if (index := self.current_sequence.used_axes.find("z")) > -1:
                scale[index] = getattr(self.current_sequence.z_plan, "step", 1)
        else:
            # return to default
            scale = [1.0, 1.0]
        return scale

    def sequenceFinished(self, sequence: MDASequence) -> None:
        """Finish the acquisition."""
        super().sequenceFinished(sequence)
        self._mda_running = False
        # reset the sliders position to the first step
        self.viewer.dims.current_step = [0] * len(self.viewer.dims.current_step)

    # this will be necessary when we manage to add the split channels feature
    # def _get_layer_blending(self) -> str:
    #     """Get the blending mode for the layer."""
    #     if not self.current_sequence:
    #         return "opaque"
    #     if meta := self.current_sequence.metadata.get(SEQUENCE_META_KEY, {}):
    #         return "additive" if meta.get("split_channels", False) else "opaque"
