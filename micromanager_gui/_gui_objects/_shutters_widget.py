from typing import Optional

from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets import ShuttersWidget
from qtpy import QtWidgets as QtW


class MMShuttersWidget(QtW.QWidget):
    """Create shutter widget."""

    def __init__(self, mmcore: Optional[CMMCorePlus] = None):
        super().__init__()

        self.setLayout(QtW.QHBoxLayout())
        self.layout().setSpacing(3)
        self.layout().setContentsMargins(0, 0, 0, 0)
        sizepolicy_btn = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        self.setSizePolicy(sizepolicy_btn)

        self._mmc = mmcore or CMMCorePlus.instance()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)
        self._on_cfg_loaded()

    def _on_cfg_loaded(self):

        self._clear()

        if not self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice):
            empty_shutter = ShuttersWidget("")
            self.layout().addWidget(empty_shutter)
            return

        shutters_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice))
        for d in shutters_devs:
            props = self._mmc.getDevicePropertyNames(d)
            if bool([x for x in props if "Physical Shutter" in x]):
                shutters_devs.remove(d)
                shutters_devs.insert(0, d)

        for idx, shutter in enumerate(shutters_devs):

            if idx == len(shutters_devs) - 1:
                s = ShuttersWidget(shutter)
            else:
                s = ShuttersWidget(shutter, autoshutter=False)
            s.button_text_open = shutter
            s.button_text_closed = shutter
            self.layout().addWidget(s)

    def _clear(self):
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.deleteLater()
