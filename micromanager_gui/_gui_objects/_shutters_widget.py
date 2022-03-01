from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import DeviceType
from qtpy import QtWidgets as QtW

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus, RemoteMMCore


class MMShuttersWidget(QtW.QWidget):
    """
    Contains the following objects:

    shutter_comboBox: QtW.QComboBox
    shutter_btn: QtW.QPushButton
    """

    def __init__(self, mmc: CMMCorePlus | RemoteMMCore):
        super().__init__()
        self._mmc = mmc
        self.setup_gui()

        self.shutter_list = []

        sig = self._mmc.events
        sig.configSet.connect(self._on_channel_changed)
        sig.propertyChanged.connect(self._on_property_changed)
        sig.systemConfigurationLoaded.connect(self._refresh_shutter_device)

        # connect pushbutton
        self.shutter_btn.clicked.connect(self._on_shutter_btn_clicked)

        # connect combobox
        self.shutter_comboBox.currentIndexChanged.connect(self._on_shutter_cbox_changed)

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setHorizontalSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # label
        self.shutter_label = QtW.QLabel(text="Shutters:")
        self.shutter_label.setMaximumWidth(80)
        self.shutter_label.setMinimumWidth(80)
        self.main_layout.addWidget(self.shutter_label, 0, 0)

        # combobox
        self.shutter_comboBox = QtW.QComboBox()
        self.shutter_comboBox.setMinimumWidth(200)
        self.main_layout.addWidget(self.shutter_comboBox, 0, 1)

        # pushbutton
        self.shutter_btn = QtW.QPushButton(text="Closed")
        self.shutter_btn.setStyleSheet("background-color: magenta;")
        self.shutter_btn.setMinimumWidth(80)
        self.shutter_btn.setMaximumWidth(80)
        self.main_layout.addWidget(self.shutter_btn, 0, 2)

        self.setLayout(self.main_layout)

    def _on_property_changed(self, dev_name: str, prop_name: str, value: str):
        if dev_name == self._mmc.getShutterDevice():
            self.shutter_comboBox.setCurrentText(self._mmc.getShutterDevice())

    def _on_channel_changed(self, channel_group: str, channel_preset: str):
        if channel_group == self._mmc.getChannelGroup():
            self._shutter_from_channel(channel_group, channel_preset)

    def _close_shutter(self):
        self._mmc.setShutterOpen(False)
        self.shutter_btn.setText("Closed")
        self.shutter_btn.setStyleSheet("background-color: magenta;")

    def _open_shutter(self):
        self._mmc.setShutterOpen(True)
        self.shutter_btn.setText("Opened")
        self.shutter_btn.setStyleSheet("background-color: green;")

    def _refresh_shutter_device(self):
        self.shutter_comboBox.clear()
        self.shutter_list.clear()
        for d in self._mmc.getLoadedDevices():
            if self._mmc.getDeviceType(d) == DeviceType.ShutterDevice:
                self.shutter_list.append(d)
        if self.shutter_list:
            self.shutter_comboBox.addItems(self.shutter_list)
            self._mmc.setShutterOpen(False)
            self.shutter_btn.setEnabled(True)
        else:
            self.shutter_btn.setEnabled(False)

    def _on_shutter_btn_clicked(self):
        sht = self.shutter_comboBox.currentText()
        current_sth_state = self._mmc.getShutterOpen(sht)

        if current_sth_state:  # if is open
            self._close_shutter()
        else:  # if is closed
            self._open_shutter()

    def _on_shutter_cbox_changed(self):
        sht = self.shutter_comboBox.currentText()
        self._mmc.setShutterDevice(sht)
        self._close_shutter()

    def _shutter_from_channel(self, group, channel):
        shutter_list = [
            (k[0], k[1], k[2])
            for k in self._mmc.getConfigData(group, channel)
            if self._mmc.getDeviceType(k[0]) == DeviceType.ShutterDevice
        ]

        if not shutter_list:
            return

        if len(shutter_list) > 1:
            self.shutter_comboBox.setCurrentText("Multi Shutter")
        else:
            self.shutter_comboBox.setCurrentText(shutter_list[0])

    # def _multishutter_from_channel(self):
    #     channel_group = self._mmc.getChannelGroup()
    #     current_channel = self._mmc.getCurrentConfig(channel_group)

    #     multishutter_list = [
    #         (k[0], k[1], k[2])
    #         for k in self._mmc.getConfigData(channel_group, current_channel)
    #         if k[0] == "Multi Shutter"
    #     ]

    #     if not multishutter_list:
    #         return

    #     for d, p, v in multishutter_list:
    #         self._mmc.setProperty(d, p, v)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMShuttersWidget()
    win.show()
    sys.exit(app.exec_())
