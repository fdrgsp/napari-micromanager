import atexit
import contextlib
import tempfile
from typing import TYPE_CHECKING, Dict, Generator, Optional

import napari
import numpy as np
import zarr
from cellpose.models import CellposeModel
from napari.qt.threading import thread_worker
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import PMDAEngine
from qtpy.QtWidgets import QCheckBox, QDialog, QVBoxLayout, QWidget
from useq import MDAEvent, MDASequence

from micromanager_gui._util import event_indices

if TYPE_CHECKING:
    import napari.viewer


class CellposeWidget(QDialog):
    """Widget to run Cellpose when core emits 'frameReady' signal."""

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ) -> None:
        super().__init__(parent)

        self._cellpose_is_active = False

        self.viewer = viewer

        self._mmc = mmcore or CMMCorePlus.instance()

        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)
        self._mmc.mda.events.sequenceStarted.connect(self._create_zarr)
        self._mmc.mda.events.frameReady.connect(self._cellpose_module)

        self.destroyed.connect(self._disconnect)

        self._mda_temp_arrays: Dict[str, zarr.Array] = {}
        self._mda_temp_files: Dict[str, tempfile.TemporaryDirectory] = {}

        self._create_cellpose_wdg()

        @atexit.register
        def cleanup():
            """Clean up temporary files we opened."""
            for v in self._mda_temp_files.values():
                with contextlib.suppress(NotADirectoryError):
                    v.cleanup()

    def _create_cellpose_wdg(self):

        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        self._cellpose_checkbox = QCheckBox(text="activate Cellpose")
        self._cellpose_checkbox.toggled.connect(self._on_cellpose_checkbox_toggle)
        main_layout.addWidget(self._cellpose_checkbox)

    def _on_cellpose_checkbox_toggle(self, state: bool):
        self._cellpose_is_active = state

    def _disconnect(self):
        self._mmc.events.mdaEngineRegistered.disconnect(self._update_mda_engine)
        self._mmc.mda.events.sequenceStarted.disconnect(self._create_zarr)
        self._mmc.mda.events.frameReady.disconnect(self._cellpose_module)

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine) -> None:
        oldEngine.events.frameReady.disconnect(self._cellpose_module)
        newEngine.events.frameReady.connect(self._cellpose_module)

        oldEngine.events.sequenceStarted.connect(self._create_zarr)
        newEngine.events.sequenceStarted.connect(self._create_zarr)

    def _get_shape_and_labels(self, sequence: MDASequence):
        """Determine the shape of layers and the dimension labels."""
        img_shape = self._mmc.getImageHeight(), self._mmc.getImageWidth()
        axis_order = event_indices(next(sequence.iter_events()))
        shape = [sequence.shape[i] for i, a in enumerate(axis_order)]
        shape.extend(img_shape)
        return shape

    def _create_zarr(self, sequence: MDASequence):
        if not self._cellpose_is_active:
            return

        shape = self._get_shape_and_labels(sequence)
        dtype = f"uint{self._mmc.getImageBitDepth()}"

        id_ = f"cellpose_{sequence.uid}"
        tmp = tempfile.TemporaryDirectory()

        self._mda_temp_files[id_] = tmp
        self._mda_temp_arrays[id_] = z = zarr.open(
            str(tmp.name), shape=shape, dtype=dtype
        )
        layer = self.viewer.add_image(
            z, name=f"cellpose_{sequence.uid}", opacity=0.3, colormap="green"
        )
        layer.metadata["title"] = "cellpose"
        layer.metadata["uid"] = sequence.uid
        layer.metadata["useq_sequence"] = sequence

    def _cellpose_module(self, image: np.ndarray, event: MDAEvent):
        if not self._cellpose_is_active:
            return
        worker = self._run_cellpose(image, event)
        worker.yielded.connect(self._add_to_viewer)
        worker.start()

    @thread_worker
    def _run_cellpose(self, image: np.ndarray, event: MDAEvent) -> Generator:

        # TODO: set channel name before
        if event.channel.config != "Cy5":
            yield (event,)

        else:
            nuclei = "nuclei"
            nuclei_cell_diameter = 100
            model_nuclei = CellposeModel(model_type=nuclei)

            mask_nuclei, *_ = model_nuclei.eval(
                image,
                diameter=nuclei_cell_diameter,
            )
            yield (mask_nuclei, event)

        # cyto = "ctyo2"
        # cyto_cell_diameter = 180
        # cyto_mask_threshold = -2.0
        # model_cyto = CellposeModel(model_type=cyto)

        # mask_cyto, *_ = model_cyto.eval(
        #     image,
        #     diameter=cyto_cell_diameter,
        #     mask_threshold=cyto_mask_threshold,
        # )

    def _add_to_viewer(self, *args) -> None:

        if len(args[0]) == 1:
            return

        mask, event = args[0]

        axis_order = list(event_indices(event))

        im_idx = tuple(event.index[k] for k in axis_order)

        self._mda_temp_arrays[f"cellpose_{event.sequence.uid}"][im_idx] = mask
        self.viewer.layers[f"cellpose_{event.sequence.uid}"].visible = False
        self.viewer.layers[f"cellpose_{event.sequence.uid}"].visible = True
