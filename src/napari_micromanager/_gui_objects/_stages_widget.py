from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets import StageWidget
from qtpy.QtGui import QWheelEvent
from qtpy.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QMenu,
    QSizePolicy,
    QWidget,
)

from ._kinesis_rotation_widget import KinesisRotationWidget

STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage}


class Group(QGroupBox):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._name = name

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )


class Stage(StageWidget):
    """Stage control widget with wheel event for z-axis control."""

    def __init__(self, device: str) -> None:
        super().__init__(device=device)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._dtype != DeviceType.Stage:
            return
        delta = event.angleDelta().y()
        increment = self._step.value()
        if delta > 0:
            self._move_stage(0, increment)
        elif delta < 0:
            self._move_stage(0, -increment)


class MMStagesWidget(QWidget):
    """UI elements for stage control widgets."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent=parent)

        self._stage_wdgs: list[Group] = []

        self._context_menu = QMenu(self)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._mmc = CMMCorePlus.instance()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

    def _on_cfg_loaded(self) -> None:
        self._clear()
        sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        stage_dev_list = list(self._mmc.getLoadedDevicesOfType(DeviceType.XYStage))
        stage_dev_list.extend(iter(self._mmc.getLoadedDevicesOfType(DeviceType.Stage)))
        for idx, stage_dev in enumerate(stage_dev_list):
            if self._mmc.getDeviceType(stage_dev) is DeviceType.XYStage:
                bx = Group("XY Control")
            elif self._mmc.getDeviceType(stage_dev) is DeviceType.Stage:
                bx = Group("Z Control")
            else:
                continue

            self._stage_wdgs.append(bx)
            bx.setSizePolicy(sizepolicy)
            if stage_dev == "KBD101_28252107":
                bx.layout().addWidget(KinesisRotationWidget("KBD101_28252107"))
            else:
                bx.layout().addWidget(Stage(device=stage_dev))

            self._layout.addWidget(bx, idx // 2, idx % 2)

        self.resize(self.sizeHint())

    def _clear(self) -> None:
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(QWidget())
                    wdg.deleteLater()
