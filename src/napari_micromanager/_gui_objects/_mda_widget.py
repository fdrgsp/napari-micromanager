from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_widgets.mda import MDAWidget
from qtpy.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence


MMCORE_WIDGETS_META = "pymmcore_widgets"


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout.addWidget(self.checkBox_split_channels)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = super().value()
        split = self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda", split_channels=bool(split)
        )
        return sequence  # type: ignore[no-any-return]

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        if nmm_meta := value.metadata.get(SEQUENCE_META_KEY):
            if isinstance(nmm_meta, dict):
                nmm_meta = SequenceMeta(**nmm_meta)
            if not isinstance(nmm_meta, SequenceMeta):  # pragma: no cover
                raise TypeError(f"Expected {SequenceMeta}, got {type(nmm_meta)}")
            # set split_channels checkbox
            self.checkBox_split_channels.setChecked(bool(nmm_meta.split_channels))
        super().setValue(value)
