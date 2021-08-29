from enum import IntEnum

import pymmcore
from magicgui import magicgui
from magicgui.widgets import Container
from pymmcore_plus import RemoteMMCore


# WHY mmc.getDeviceType(dev) does g9ve a number and not a type?
class DeviceType(IntEnum):
    UnknownType = getattr(pymmcore, "UnknownType")
    AnyType = getattr(pymmcore, "AnyType")
    CameraDevice = getattr(pymmcore, "CameraDevice")
    ShutterDevice = getattr(pymmcore, "ShutterDevice")
    StateDevice = getattr(pymmcore, "StateDevice")
    StageDevice = getattr(pymmcore, "StageDevice")
    XYStageDevice = getattr(pymmcore, "XYStageDevice")
    SerialDevice = getattr(pymmcore, "SerialDevice")
    GenericDevice = getattr(pymmcore, "GenericDevice")
    AutoFocusDevice = getattr(pymmcore, "AutoFocusDevice")
    CoreDevice = getattr(pymmcore, "CoreDevice")
    ImageProcessorDevice = getattr(pymmcore, "ImageProcessorDevice")
    SignalIODevice = getattr(pymmcore, "SignalIODevice")
    MagnifierDevice = getattr(pymmcore, "MagnifierDevice")
    SLMDevice = getattr(pymmcore, "SLMDevice")
    HubDevice = getattr(pymmcore, "HubDevice")
    GalvoDevice = getattr(pymmcore, "GalvoDevice")


mmc = RemoteMMCore()
mmc.loadSystemConfiguration("micromanager_gui/demo_config.cfg")


c = Container(labels=False)

for dev in mmc.getLoadedDevices():
    dev_type = DeviceType(mmc.getDeviceType(dev))
    for prop in mmc.getDevicePropertyNames(dev):
        has_range = mmc.hasPropertyLimits(dev, prop)
        lower_lim = mmc.getPropertyLowerLimit(dev, prop)
        upper_lim = mmc.getPropertyUpperLimit(dev, prop)
        if has_range:
            print(dev, dev_type, prop, has_range, lower_lim, upper_lim)

            @magicgui(
                auto_call=True,
                layout="vertical",
                slider_float={
                    "label": f"{dev}_{prop}",
                    "widget_type": "FloatSlider",
                    "max": upper_lim,
                    "min": lower_lim,
                },
            )
            def sl(slider_float):
                print(slider_float)

            c.append(sl)

c.show(run=True)
