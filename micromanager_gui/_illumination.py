import sys
from pathlib import Path

from pymmcore_plus import RemoteMMCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtWidgets import QApplication

from magicgui import magicgui
from magicgui.widgets import Container
from pymmcore_plus import RemoteMMCore




class Illumination(Container):

    def __init__(self,  mmcore: RemoteMMCore):
        super().__init__()

        self._mmc = mmcore

        self.light_list = ['dia', 'epi', 'lumencor']

        self.make_magicgui()

    def make_magicgui(self):
        c = Container(labels=False)
        for cfg in self._mmc.getAvailableConfigGroups():
            cfg_lower = cfg.lower()
            if cfg_lower in self.light_list:
                cfg_groups_options = self._mmc.getAvailableConfigs(cfg)
                cfg_groups_options_keys = (
                    self._mmc.getConfigData(cfg, cfg_groups_options[0])
                ).dict()

                dev_name = [k for idx, k in enumerate(cfg_groups_options_keys.keys()) if idx == 0][0]

                for prop in self._mmc.getDevicePropertyNames(dev_name):
                    has_range = self._mmc.hasPropertyLimits(dev_name, prop)
                    lower_lim = self._mmc.getPropertyLowerLimit(dev_name, prop)
                    upper_lim = self._mmc.getPropertyUpperLimit(dev_name, prop)

                    if has_range and 'intensity' in str(prop).lower():
                        # print(dev_name, prop, has_range, lower_lim, upper_lim)

                        @magicgui(
                            auto_call=True,
                            layout="vertical",
                            dev_name={'bind': dev_name},
                            prop={'bind': prop},
                            slider_float={
                                "label": f"{dev_name}_{prop}",
                                "widget_type": "FloatSlider",
                                "max": upper_lim,
                                "min": lower_lim,
                            },
                        )
                        def sld(dev_name,prop,slider_float=10):
                            self._mmc.setProperty(dev_name,prop,slider_float)
                            print(prop, self._mmc.getProperty(dev_name,prop))

                        c.append(sld)

        c.show(run=True)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    mmcore = RemoteMMCore()
    mmcore.loadSystemConfiguration("micromanager_gui/s15_Nikon_Ti1.cfg")
    cls = Illumination(mmcore)
    cls.show(run=True)
    sys.exit(app.exec_())
