import sys

from magicgui import magicgui
from magicgui.widgets import Container
from pymmcore_plus import RemoteMMCore
from qtpy.QtWidgets import QApplication


class Illumination(Container):
    def __init__(self, mmcore: RemoteMMCore):
        super().__init__()

        self._mmc = mmcore

        self.light_list = ["dia", "epi", "lumencor"]
        # self.light_list = ["dia", "epi", "lumencor", "dia_fake", "epi_fake"]

    def make_magicgui(self):
        c = Container(labels=False)
        for cfg in self._mmc.getAvailableConfigGroups():
            cfg_lower = cfg.lower()

            if cfg_lower in self.light_list:
                cfg_groups_options = self._mmc.getAvailableConfigs(cfg)
                cfg_groups_options_keys = (
                    self._mmc.getConfigData(cfg, cfg_groups_options[0])
                ).dict()

                dev_name = [
                    k
                    for idx, k in enumerate(cfg_groups_options_keys.keys())
                    if idx == 0
                ][0]

                print(cfg, dev_name)

                for prop in self._mmc.getDevicePropertyNames(dev_name):
                    has_range = self._mmc.hasPropertyLimits(dev_name, prop)
                    lower_lim = self._mmc.getPropertyLowerLimit(dev_name, prop)
                    upper_lim = self._mmc.getPropertyUpperLimit(dev_name, prop)
                    is_float = isinstance(upper_lim, float)

                    if has_range and "intensity" in str(prop).lower():
                        # if has_range and ("exposure" in str(prop).lower()):
                        # print(dev_name, prop, has_range, lower_lim, upper_lim)
                        print(prop, is_float)
                        if is_float:
                            slider_type = "FloatSlider"
                            slider_value = float(self._mmc.getProperty(dev_name, prop))
                        else:
                            slider_type = "Slider"
                            slider_value = self._mmc.getProperty(dev_name, prop)

                        @magicgui(
                            auto_call=True,
                            layout="vertical",
                            dev_name={"bind": dev_name},
                            prop={"bind": prop},
                            slider={
                                "label": f"{dev_name}_{prop}",
                                "widget_type": slider_type,
                                "max": upper_lim,
                                "min": lower_lim,
                            },
                        )
                        def sld(dev_name, prop, slider=slider_value):
                            self._mmc.setProperty(dev_name, prop, slider)
                            print(prop, self._mmc.getProperty(dev_name, prop))

                        c.append(sld)
        c.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mmcore = RemoteMMCore()
    # mmcore.loadSystemConfiguration("micromanager_gui/s15_Nikon_Ti1.cfg")
    mmcore.loadSystemConfiguration("micromanager_gui/demo_config_test.cfg")
    cls = Illumination(mmcore)
    cls.make_magicgui()
    sys.exit(app.exec_())
