from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_widgets.mda import MDAWidget
from qtpy.QtWidgets import QBoxLayout, QCheckBox, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence


from napari_micromanager._util import NMM_METADATA_KEY


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split channels in viewer")
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout.addWidget(self.checkBox_split_channels)

        layout = cast("QBoxLayout", self.layout())
        self._stage_scan_cbox = QCheckBox("Use Stage Scan Mode")
        self._stage_scan_cbox.setToolTip(
            """
            Use the stage scan mode for the acquisition.

            This mode is useful if you want to first scan your sample using any 'grid
            plan' (single- or multi-channel) and then draw on the stitched image the
            areas that you want to acquire with different parameters (e.g. different
            objective, z-stack, ...).

            NOTE: this mode is not compatible only works if you only select the channels
            tab and one of the grid plans (no other MDA Tabs should be checked).
            """
        )
        layout.insertWidget(4, self._stage_scan_cbox)
        layout.insertStretch(5, 1)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = super().value()
        split = self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
        sequence.metadata[NMM_METADATA_KEY] = {
            "split_channels": split,
            "stage_scan": self._stage_scan_cbox.isChecked(),
        }
        return sequence  # type: ignore[no-any-return]

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        # set split_channels checkbox
        if nmm_meta := value.metadata.get(NMM_METADATA_KEY):
            self.checkBox_split_channels.setChecked(
                nmm_meta.get("split_channels", False)
            )
            self._stage_scan_cbox.setChecked(nmm_meta.get("stage_scan", False))
        super().setValue(value)
