from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import napari
import zarr
from qtpy.QtWidgets import QMessageBox

from ._util import NMM_METADATA_KEY

if TYPE_CHECKING:
    import napari.viewer
    import numpy as np
    import useq
    from pymmcore_plus import CMMCorePlus


class RowsCols(NamedTuple):
    """A simple named tuple to store the row and column of a grid plan."""

    row: int
    col: int


class _StageScan:
    """A class to handle the stage scan with grid plans."""

    def __init__(self, mmcore: CMMCorePlus, viewer: napari.viewer.Viewer) -> None:
        self._mmc = mmcore
        self._viewer = viewer
        self._mda_running: bool = False

        self._z: zarr.Array | None = None
        self._rows_cols: list[RowsCols] = []

        self._stage_scan: bool = False

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_sequence_finished)
        self._mmc.mda.events.frameReady.connect(self._on_frame_ready)

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        self._mda_running = True

        meta = sequence.metadata.get(NMM_METADATA_KEY)
        self._stage_scan = bool(meta.get("stage_scan")) if meta else False

        if not self._stage_scan:
            return

        if sequence.grid_plan is None:
            self._raise_stage_scan_sequence_error()
            return

        if len(sequence.stage_positions) > 1:
            self._raise_stage_scan_sequence_error()
            return

        # if there is only one position but it has sub-sequence, we return
        if (
            len(sequence.stage_positions) == 1
            and sequence.stage_positions[0].sequence is not None
        ):
            self._raise_stage_scan_sequence_error()
            return

        ch = len(sequence.channels)
        grid = sequence.grid_plan

        self._rows_cols = [
            RowsCols(i.row, i.col)
            for i in grid
            if RowsCols(i.row, i.col) not in self._rows_cols
        ]

        rows = max(i.row for i in self._rows_cols)
        cols = max(i.col for i in self._rows_cols)

        width = self._mmc.getImageWidth() * (cols + 1)
        height = self._mmc.getImageHeight() * (rows + 1)

        self._z = zarr.open(
            shape=(ch, height, width),
            dtype=f"u{self._mmc.getBytesPerPixel()}",
            chunks=(1, self._mmc.getImageWidth(), self._mmc.getImageHeight()),
        )

        self._layer = self._viewer.add_image(self._z, name="Scan")
        self._viewer.dims.axis_labels = ("c", "y", "x")

    def _raise_stage_scan_sequence_error(self) -> None:
        self._z = None
        self._rows_cols.clear()
        self._mmc.mda.cancel()
        msg = (
            "To use the 'Stage Scan' mode, the MDASequence must have a single- or a "
            "multi-channel grid plan, it can have maximum one position "
            "(with no sub-sequence) and no other dimension."
        )
        QMessageBox.critical(
            self._viewer.window._qt_viewer,
            "Stage Scan Error",
            msg,
            QMessageBox.StandardButton.Ok,
        )

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        self._mda_running = False

        if not self._stage_scan:
            return

        self._rows_cols.clear()

    def _on_frame_ready(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        if not self._stage_scan:
            return

        if self._z is None:
            return

        if event.x_pos is None or event.y_pos is None:
            return

        ch = event.index.get("c", 0)
        g = event.index.get("g", 0)

        row_col = self._rows_cols[g]

        # store the top-left corner event to later get the shape layer stage position
        if row_col.row == 0 and row_col.col == 0:
            self._layer.metadata["event"] = event
            self._layer.metadata["top_left"] = (
                event.x_pos - ((image.shape[1] / 2) * self._mmc.getPixelSizeUm()),
                event.y_pos + ((image.shape[0] / 2) * self._mmc.getPixelSizeUm()),
            )

        # add the image to the zarr array depending on the grid row and column
        # by calculating the correct offset based on the image size
        row_start = row_col.row * self._mmc.getImageHeight()
        row_end = row_start + image.shape[0]
        col_start = row_col.col * self._mmc.getImageWidth()
        col_end = col_start + image.shape[1]

        self._z[ch, row_start:row_end, col_start:col_end] = image

        self._layer.visible = False
        self._layer.visible = True

    def _cleanup(self) -> None: ...
