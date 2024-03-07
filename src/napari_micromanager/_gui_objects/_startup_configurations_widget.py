from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from warnings import warn

from platformdirs import user_config_dir
from pymmcore_plus import CMMCorePlus, find_micromanager
from pymmcore_widgets import ConfigWizard
from pymmcore_widgets.hcwizard.finish_page import DEST_CONFIG
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

USER_DIR = Path(user_config_dir("napari_micromanager"))
USER_CONFIGS_PATHS = USER_DIR / "system_configurations.json"
FIXED = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
NEW = "New Hardware Configuration"


def _add_path_to_json(path: Path | str) -> None:
    """Uopdate the json file with the new path."""
    if isinstance(path, Path):
        path = str(path)

    # create USER_CONFIGS_PATHS if it doesn't exist
    if not USER_CONFIGS_PATHS.exists():
        USER_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIGS_PATHS, "w") as f:
            json.dump({"paths": []}, f)

    # Read the existing data
    try:
        with open(USER_CONFIGS_PATHS) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = {"paths": []}

    # Append the new path. using insert so we leave the empty string at the end
    paths = cast(list, data.get("paths", []))
    if path not in paths:
        paths.insert(0, path)

    # Write the data back to the file
    with open(USER_CONFIGS_PATHS, "w") as f:
        json.dump({"paths": paths}, f)


def _load_system_configuration(mmcore: CMMCorePlus, config: str | Path) -> None:
    """Load a Micro-Manager system configuration file."""
    try:
        mmcore.loadSystemConfiguration(config)
    except FileNotFoundError:
        # don't crash if the user passed an invalid config
        warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)


class StartupConfigurations(QDialog):
    """A dialog to select the Micro-Manager Hardware configuration files at startup."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        config: Path | str | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Micro-Manager Hardware System Configurations")

        self._mmc = mmcore or CMMCorePlus.instance()
        self._config = config

        # label
        cfg_lbl = QLabel("Configuration file:")
        cfg_lbl.setSizePolicy(FIXED)

        # combo box
        self.cfg_combo = QComboBox()
        # `AdjustToMinimumContents` is not available in all qtpy backends so using
        # `AdjustToMinimumContentsLengthWithIcon` instead
        self.cfg_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        # browse button
        self.browse_btn = QPushButton("...")
        self.browse_btn.setSizePolicy(FIXED)
        self.browse_btn.clicked.connect(self._on_browse_clicked)

        # Create OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # add widgets to layout
        wdg_layout = QGridLayout(self)
        wdg_layout.addWidget(cfg_lbl, 0, 0)
        wdg_layout.addWidget(self.cfg_combo, 0, 1)
        wdg_layout.addWidget(self.browse_btn, 0, 2)
        wdg_layout.addWidget(button_box, 2, 0, 1, 3)

        self._initialize()

        # if a config was not passed, show the dialog
        if config is None:
            if self.exec_():
                config = self.cfg_combo.currentText()
                # if the user selected NEW, show the config wizard
                if config == NEW:
                    self._cfg_wizard = HardwareConfigWizard(parent=self)
                    self._cfg_wizard.show()
                # otherwise load the selected config
                else:
                    _load_system_configuration(self._mmc, config)
        # if a config was passed, load it
        else:
            _load_system_configuration(self._mmc, config)

    def _initialize(self) -> None:
        """Initialize the dialog with the configuration files.

        This method reads the stored paths in the USER_CONFIGS_PATHS jason file (or
        create one if it doesn't exist) and adds them to the combo box. It also adds the
        Micro-Manager configuration files form the Micro-Manager folder if they are not
        already in the list.
        """
        # create USER_CONFIGS_PATHS if it doesn't exist
        if not USER_CONFIGS_PATHS.exists():
            USER_DIR.mkdir(parents=True, exist_ok=True)
            with open(USER_CONFIGS_PATHS, "w") as f:
                json.dump({"paths": []}, f)

        # get the paths from the json file
        configs_paths = self._get_config_paths()

        # add the paths to the combo box
        self.cfg_combo.addItems([*configs_paths, NEW])

        # write the data back to the file
        with open(USER_CONFIGS_PATHS, "w") as f:
            json.dump({"paths": configs_paths}, f)

        self.resize(600, self.minimumSizeHint().height())

    def _get_config_paths(self) -> list[str]:
        """Return the paths from the json file.

        If a file stored in the json file doesn't exist, it is removed from the list.

        The method also adds all the .cfg files in the MicroManager folder to the list
        if they are not already there.
        """
        try:
            with open(USER_CONFIGS_PATHS) as f:
                data = json.load(f)

            # get path list from json file
            paths = cast(list, data.get("paths", []))

            # remove any path that doesn't exist
            for path in paths:
                if not Path(path).exists():
                    paths.remove(path)

            # get all the .cfg files in the MicroManager folder
            cfg_files = self._get_micromanager_cfg_files()

            # add all the .cfg files to the list if they are not already there
            for cfg in reversed(cfg_files):
                if str(cfg) not in paths:
                    # using insert so we leave the empty string at the end
                    paths.insert(0, str(cfg))

            # if a config was passed, add it to the list if it's not already there
            if self._config is not None and str(self._config) not in paths:
                paths.insert(0, str(self._config))

        except json.JSONDecodeError:
            paths = []
            warn("Error reading the json file.", stacklevel=2)

        return paths

    def _get_micromanager_cfg_files(self) -> list[Path]:
        """Return all the .cfg files from all the MicroManager folders."""
        mm: list = find_micromanager(False)
        cfg_files: list[Path] = []
        for mm_dir in mm:
            cfg_files.extend(Path(mm_dir).glob("*.cfg"))

        return cfg_files

    def _on_browse_clicked(self) -> None:
        """Open a file dialog to select a file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "MicroManager files (*.cfg)"
        )
        if path:
            # using insert so we leave the empty string at the end
            self.cfg_combo.insertItem(0, path)
            self.cfg_combo.setCurrentText(path)
            _add_path_to_json(path)


class HardwareConfigWizard(ConfigWizard):
    """A wizard to create a new Micro-Manager hardware configuration file.

    Subclassing to load the newly created configuration file and to add it to the
    USER_CONFIGS_PATHS json file.
    """

    def __init__(
        self,
        config_file: str = "",
        core: CMMCorePlus | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(config_file, core, parent)

        self.setWindowTitle("Micro-Manager Hardware Configuration Wizard")

    def accept(self) -> None:
        """Accept the wizard and save the configuration to a file.

        Overriding to add the new configuration file to the USER_CONFIGS_PATHS json file
        and to load it.
        """
        dest = self.field(DEST_CONFIG)
        _add_path_to_json(dest)
        super().accept()
        _load_system_configuration(self._core, dest)
