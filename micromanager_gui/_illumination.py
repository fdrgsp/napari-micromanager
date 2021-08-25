import sys
from pathlib import Path

from pymmcore_plus import RemoteMMCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtWidgets import QApplication

UI_FILE = str(Path(__file__).parent / "_ui" / "illumination.ui")


class Illumination(QtW.QWidget):

    btn: QtW.QPushButton

    def __init__(self, mmcore: RemoteMMCore, parent=None):

        self._mmc = mmcore
        super().__init__(parent)
        uic.loadUi(UI_FILE, self)

        self.btn.clicked.connect(self.get_groups_list)

    def get_groups_list(self):
        group = []
        for groupName in self._mmc.getAvailableConfigGroups():
            print(f"*********\nGroup_Name: {str(groupName)}")
            for configName in self._mmc.getAvailableConfigs(groupName):
                group.append(configName)
                print(f"Config_Name: {str(configName)}")
                gdc = self._mmc.getConfigData(groupName, configName).getVerbose()
                print(f"Properties: {str(gdc)}")
            print("*********")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mmcore = RemoteMMCore()
    # mmcore.loadSystemConfiguration("micromanager_gui/demo_config.cfg")
    cls = Illumination(mmcore)
    cls.show()
    sys.exit(app.exec_())
