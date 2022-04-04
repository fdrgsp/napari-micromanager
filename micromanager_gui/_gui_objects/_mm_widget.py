from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt import QCollapsible

from ._camera_widget import MMCameraWidget
from ._config_widget import MMConfigurationWidget
from ._hcs_widget._main_hcs_widget import HCSWidget
from ._mda_widget import MultiDWidget
from ._objective_widget import MMObjectivesWidget
from ._sample_explorer_widget import ExploreSample
from ._shutters_widget import MMShuttersWidget
from ._slider_dialog import SliderDialog
from ._tab_widget import MMTabWidget
from ._xyz_stages import MMStagesWidget


class MicroManagerWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        # sub_widgets
        self.cfg_wdg = MMConfigurationWidget()
        self.obj_wdg = MMObjectivesWidget()
        self.cam_wdg = MMCameraWidget()
        self.stage_wdg = MMStagesWidget()
        self.illum_btn = QtW.QPushButton("Light Sources")
        self.illum_btn.clicked.connect(self._show_illum_dialog)
        self.tab_wdg = MMTabWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.mda = MultiDWidget()
        self.explorer = ExploreSample()
        self.hcs = HCSWidget(self)

        self.create_gui()

    def create_gui(self):

        # main widget
        self.main_layout = QtW.QVBoxLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # add cfg_wdg
        self.main_layout.addWidget(self.cfg_wdg)

        # add microscope collapsible
        self.mic_group = QtW.QGroupBox()
        self.mic_group_layout = QtW.QVBoxLayout()
        self.mic_group_layout.setSpacing(0)
        self.mic_group_layout.setContentsMargins(1, 0, 1, 1)
        self.mic_coll = QCollapsible(title="Microscope")
        self.mic_coll.layout().setSpacing(0)
        self.mic_coll.layout().setContentsMargins(0, 0, 5, 10)

        # add objective, property browser, illumination and camera widgets
        obj_prop = self.add_mm_objectives_and_properties_widgets()
        ill_shutter = self.add_ill_and_shutter_widgets()
        cam = self.add_camera_widget()
        self.mic_coll.addWidget(obj_prop)
        self.mic_coll.addWidget(ill_shutter)
        self.mic_coll.addWidget(cam)
        self.mic_coll.expand(animate=False)
        self.mic_group_layout.addWidget(self.mic_coll)
        self.mic_group.setLayout(self.mic_group_layout)
        self.main_layout.addWidget(self.mic_group)

        # add stages collapsible
        self.stages_group = QtW.QGroupBox()
        self.stages_group_layout = QtW.QVBoxLayout()
        self.stages_group_layout.setSpacing(0)
        self.stages_group_layout.setContentsMargins(1, 0, 1, 1)

        self.stages_coll = QCollapsible(title="Stages")
        self.stages_coll.layout().setSpacing(0)
        self.stages_coll.layout().setContentsMargins(0, 0, 5, 10)
        self.stages_coll.addWidget(self.stage_wdg)
        self.stages_coll.expand(animate=False)

        self.stages_group_layout.addWidget(self.stages_coll)
        self.stages_group.setLayout(self.stages_group_layout)
        self.main_layout.addWidget(self.stages_group)

        self.tab_wdg.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tab_wdg.tabWidget.addTab(self.explorer, "Sample Explorer")
        self.tab_wdg.tabWidget.addTab(self.hcs, "HCS")

        # add tab widget
        self.main_layout.addWidget(self.tab_wdg)

        # set main_layout layout
        self.setLayout(self.main_layout)

    def add_camera_widget(self):
        self.cam_group = QtW.QWidget()
        self.cam_group_layout = QtW.QGridLayout()
        self.cam_group_layout.setSpacing(0)
        self.cam_group_layout.setContentsMargins(5, 5, 5, 5)
        self.cam_group_layout.addWidget(self.cam_wdg)
        self.cam_group.setLayout(self.cam_group_layout)
        return self.cam_group

    def add_mm_objectives_and_properties_widgets(self):
        obj_prop_wdg = QtW.QWidget()
        obj_prop_wdg_layout = QtW.QHBoxLayout()
        obj_prop_wdg_layout.setContentsMargins(5, 5, 5, 5)
        obj_prop_wdg_layout.setSpacing(7)
        obj_prop_wdg_layout.addWidget(self.obj_wdg)
        obj_prop_wdg.setLayout(obj_prop_wdg_layout)
        return obj_prop_wdg

    def add_ill_and_shutter_widgets(self):
        ill_shutter_wdg = QtW.QWidget()
        ill_shutter_wdg_layout = QtW.QHBoxLayout()
        ill_shutter_wdg_layout.setContentsMargins(5, 5, 5, 5)
        ill_shutter_wdg_layout.setSpacing(7)
        ill_shutter_wdg_layout.addWidget(self.shutter_wdg)
        ill_shutter_wdg_layout.addWidget(self.illum_btn)
        ill_shutter_wdg.setLayout(ill_shutter_wdg_layout)
        return ill_shutter_wdg

    def _show_illum_dialog(self):
        if not hasattr(self, "_illumination"):
            self._illumination = SliderDialog("(Intensity|Power|test)s?", self)
        self._illumination.show()
