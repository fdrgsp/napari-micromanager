import contextlib
from typing import cast

import napari.viewer
import zarr
from numpy import ndarray
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import OMEZarrWriter
from pymmcore_widgets.useq_widgets._mda_sequence import PYMMCW_METADATA_KEY
from useq import MDAEvent, MDASequence

from napari_micromanager._mda_meta import SEQUENCE_META_KEY  # to be removed

POS_PREFIX = "p"
EXP = "MDA"


class _Handler(OMEZarrWriter):
    def __init__(self, viewer: napari.viewer.Viewer, mmcore: CMMCorePlus | None = None):
        super().__init__()

        self._mmc = mmcore or CMMCorePlus.instance()
        self.viewer = viewer

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
        self._reset()
        super().sequenceStarted(sequence)

        # get filename from sequence metadata
        if meta := cast(dict, sequence.metadata.get(PYMMCW_METADATA_KEY, {})):
            self._fname = cast(str, meta.get("save_name"))
            if self._fname:
                # remove extension
                self._fname = self._fname.rsplit(".", 1)[0]  # ['test.ome', 'tiff']
                if self._fname.endswith(".ome"):
                    self._fname = self._fname.replace(".ome", "")
            else:
                self._fname = EXP

    def _reset(self) -> None:
        """Reset the handler to a clean state."""
        self._group = zarr.group()
        self.position_arrays.clear()
        self._fname = EXP

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
        layers_uid_meta = [
            layer.metadata.get("sequence_uid")
            for layer in self.viewer.layers
            if layer.metadata.get("sequence_uid") is not None
        ]

        # if the current sequence uid is not in the layers metadata, add the image
        if self.current_sequence.uid not in layers_uid_meta:
            self.viewer.add_image(
                self.position_arrays[key],
                name=layer_name,
                blending=self._get_layer_blending(),
                metadata={"sequence_uid": self.current_sequence.uid},
                scale=self._get_scale(key),
            )
            # TODO: add axis label to sliders. we can get them from the zarr attrs
            # _ARRAY_DIMENSIONS. NOTE: Maybe we also need to find a way to change
            # the visibility of the sliders and the axis labels when we click on a
            # specific layer.

        # update the slider position
        elif self._mda_running:
            cs = list(self.viewer.dims.current_step)
            index = tuple(event.index[k] for k in self.position_sizes[p_index])
            for a, v in enumerate(index):
                cs[a] = v
            self.viewer.dims.current_step = cs

    def _get_layer_blending(self) -> str:
        """Get the blending mode for the layer."""
        if not self.current_sequence:
            return "opaque"
        if meta := self.current_sequence.metadata.get(SEQUENCE_META_KEY, {}):
            return "additive" if meta.get("split_channels", False) else "opaque"
        else:
            return "opaque"

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
