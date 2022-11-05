import atexit
import contextlib
import tempfile
from typing import TYPE_CHECKING, Dict, Generator, List, Optional

import napari
import numpy as np
import zarr
from cellpose.models import CellposeModel
from napari.qt.threading import thread_worker
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import PMDAEngine
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from useq import MDAEvent, MDASequence

from . import _mda_meta
from ._util import event_indices

if TYPE_CHECKING:
    import napari.viewer


class CellposeWidget(QDialog):
    """Widget to run Cellpose when core emits 'frameReady' signal."""

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        metadata_from_wdgs: List[QWidget] = None,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ) -> None:
        super().__init__(parent)

        self._cellpose_is_active = False

        self._mda_meta: _mda_meta.SequenceMeta = None  # type: ignore
        self._meta_wdgs = metadata_from_wdgs
        self._update_and_connect_meta_wdgs()

        self.viewer = viewer

        self._mmc = mmcore or CMMCorePlus.instance()

        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)
        self._mmc.mda.events.sequenceStarted.connect(self._create_zarr)
        self._mmc.mda.events.frameReady.connect(self._cellpose_module)

        self._mmc.events.channelGroupChanged.connect(self._reset_channel_list)
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

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

    def _on_cfg_loaded(self):
        self._cellpose_checkbox.setChecked(False)
        self._reset_channel_list()

    def _update_and_connect_meta_wdgs(self):
        if self._meta_wdgs is None:
            self._meta_wdgs = []
        for wdg in self._meta_wdgs:
            wdg.metadataInfo.connect(self._on_meta_info)

    def _create_cellpose_wdg(self):

        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        self._cellpose_checkbox = QCheckBox(text="activate Cellpose")
        self._cellpose_checkbox.toggled.connect(self._on_cellpose_checkbox_toggle)
        main_layout.addWidget(self._cellpose_checkbox)

        ch = QWidget()
        ch_layout = QHBoxLayout()
        ch_layout.setSpacing(5)
        ch_layout.setContentsMargins(0, 0, 0, 0)
        ch.setLayout(ch_layout)
        ch_lbl = QLabel(text="nuclei channel:")
        self._cellpose_channel = QComboBox()
        self._reset_channel_list()
        ch_layout.addWidget(ch_lbl)
        ch_layout.addWidget(self._cellpose_channel)
        main_layout.addWidget(ch)

        nuclei_size_wdg = QWidget()
        nuclei_size_layout = QHBoxLayout()
        nuclei_size_layout.setSpacing(5)
        nuclei_size_layout.setContentsMargins(0, 0, 0, 0)
        nuclei_size_wdg.setLayout(nuclei_size_layout)
        nuclei_size_lbl = QLabel(text="nuclei min size:")
        self._cellpose_nuclei_diameter = QSpinBox()
        self._cellpose_nuclei_diameter.setAlignment(Qt.AlignCenter)
        self._cellpose_nuclei_diameter.setMaximum(10000)
        nuclei_size_layout.addWidget(nuclei_size_lbl)
        nuclei_size_layout.addWidget(self._cellpose_nuclei_diameter)
        main_layout.addWidget(nuclei_size_wdg)

    def _on_meta_info(
        self, meta: _mda_meta.SequenceMeta, sequence: MDASequence
    ) -> None:
        self._mda_meta = _mda_meta.SEQUENCE_META.get(sequence, meta)

    def _reset_channel_list(self):
        self._cellpose_channel.clear()

        if not self._mmc.getChannelGroup():
            return

        self._cellpose_channel.addItems(
            list(self._mmc.getAvailableConfigs(self._mmc.getChannelGroup()))
        )

    def _on_cellpose_checkbox_toggle(self, state: bool):
        self._cellpose_is_active = state

    def _disconnect(self):
        self._mmc.events.mdaEngineRegistered.disconnect(self._update_mda_engine)
        self._mmc.mda.events.sequenceStarted.disconnect(self._create_zarr)
        self._mmc.mda.events.frameReady.disconnect(self._cellpose_module)

        self._mmc.events.channelGroupChanged.disconnect(self._reset_channel_list)
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

        for wdg in self._meta:
            wdg.metadataInfo.disconnect(self._on_meta_info)

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine) -> None:
        oldEngine.events.frameReady.disconnect(self._cellpose_module)
        newEngine.events.frameReady.connect(self._cellpose_module)

        oldEngine.events.sequenceStarted.connect(self._create_zarr)
        newEngine.events.sequenceStarted.connect(self._create_zarr)

    def _get_shape_and_channels(self, sequence: MDASequence):
        """Determine the shape of layers and the dimension labels."""
        img_shape = self._mmc.getImageHeight(), self._mmc.getImageWidth()
        axis_order = event_indices(next(sequence.iter_events()))

        labels = []
        shape = []
        for i, a in enumerate(axis_order):
            dim = sequence.shape[i]
            labels.append(a)
            shape.append(dim)
        labels.extend(["y", "x"])
        shape.extend(img_shape)

        if self._mda_meta.split_channels:
            channels = [f"{c.config}_" for c in sequence.channels]
            with contextlib.suppress(ValueError):
                c_idx = labels.index("c")
                labels.pop(c_idx)
                shape.pop(c_idx)
        else:
            channels = [f"{self._cellpose_channel.currentText()}_"]

        return shape, channels

    def _create_zarr(self, sequence: MDASequence):
        if not self._cellpose_is_active:
            return

        shape, channels = self._get_shape_and_channels(sequence)

        dtype = f"uint{self._mmc.getImageBitDepth()}"

        for i, channel in enumerate(channels):

            if channel[:-1] != self._cellpose_channel.currentText():
                continue

            id_ = f"cellpose_{channel}{sequence.uid}"
            tmp = tempfile.TemporaryDirectory()

            self._mda_temp_files[id_] = tmp
            self._mda_temp_arrays[id_] = z = zarr.open(
                str(tmp.name), shape=shape, dtype=dtype
            )
            layer_name = f"cellpose_{channel}{sequence.uid}"
            layer = self.viewer.add_image(
                z, name=layer_name, opacity=0.3, colormap="green"
            )
            layer.metadata["title"] = "cellpose"
            layer.metadata["ch_id"] = f"{channel}idx{i}"
            layer.metadata["uid"] = sequence.uid
            layer.metadata["useq_sequence"] = sequence

    def _cellpose_module(self, image: np.ndarray, event: MDAEvent):
        if not self._cellpose_is_active:
            return

        if not self._mda_meta:
            return

        if self._mda_meta.mode != "mda":
            return

        worker = self._run_cellpose(image, event)
        worker.yielded.connect(self._add_to_viewer)
        worker.start()

    @thread_worker
    def _run_cellpose(self, image: np.ndarray, event: MDAEvent) -> Generator:

        if event.channel.config != self._cellpose_channel.currentText():
            yield (event,)

        else:
            nuclei = "nuclei"
            model_nuclei = CellposeModel(model_type=nuclei)

            mask_nuclei, *_ = model_nuclei.eval(
                image, diameter=self._cellpose_nuclei_diameter.value()
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

        channel = f"{self._cellpose_channel.currentText()}_"
        if self._mda_meta.split_channels:
            channel = f"{event.channel.config}_"
            # split channels checked but no channels added
            with contextlib.suppress(ValueError):
                axis_order.remove("c")

        im_idx = tuple(event.index[k] for k in axis_order)

        self._mda_temp_arrays[f"cellpose_{channel}{event.sequence.uid}"][im_idx] = mask
        self.viewer.layers[f"cellpose_{channel}{event.sequence.uid}"].visible = False
        self.viewer.layers[f"cellpose_{channel}{event.sequence.uid}"].visible = True
