from __future__ import annotations

import atexit
import contextlib
from typing import TYPE_CHECKING, Any, Callable, Generator

import napari
import numpy as np
from pymmcore_plus import CMMCorePlus
from pymmcore_plus._util import find_micromanager
from qtpy.QtCore import QPoint, QTimer
from qtpy.QtWidgets import QMenu
from superqt.utils import create_worker, ensure_main_thread

from ._gui_objects._toolbar import MicroManagerToolbar
from ._mda_handler import _NapariMDAHandler

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    from pymmcore_plus.core.events._protocol import PSignalInstance

MENU_STYLE = """
    QMenu {
        font-size: 15px;
        border: 1px solid grey;
        border-radius: 3px;
    }
"""


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`mmcore install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        super().__init__(viewer)

        # get global CMMCorePlus instance
        self._mmc = CMMCorePlus.instance()

        self._mda_handler = _NapariMDAHandler(self._mmc, viewer)
        self.streaming_timer: QTimer | None = None

        # Add all core connections to this list.  This makes it easy to disconnect
        # from core when this widget is closed.
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self._mmc.events.exposureChanged, self._update_live_exp),
            (self._mmc.events.imageSnapped, self._update_viewer),
            (self._mmc.events.imageSnapped, self._stop_live),
            (self._mmc.events.continuousSequenceAcquisitionStarted, self._start_live),
            (self._mmc.events.sequenceAcquisitionStopped, self._stop_live),
            (self.viewer.layers.events, self._update_max_min),
            (self.viewer.layers.selection.events, self._update_max_min),
            (self.viewer.dims.events.current_step, self._update_max_min),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

        # add minmax dockwidget
        self.viewer.window.add_dock_widget(self.minmax, name="MinMax", area="left")

        self.viewer.mouse_drag_callbacks.append(self._mouse_right_click)

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        self._mda_handler._cleanup()
        atexit.unregister(self._cleanup)  # doesn't raise if not connected

    @ensure_main_thread  # type: ignore [misc]
    def _update_viewer(self, data: np.ndarray | None = None) -> None:
        """Update viewer with the latest image from the circular buffer."""
        if data is None:
            try:
                data = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")

        preview_layer.metadata["mode"] = "preview"
        preview_layer.metadata["positions"] = [
            (
                [],
                self._mmc.getXPosition() if self._mmc.getXYStageDevice() else None,
                self._mmc.getYPosition() if self._mmc.getXYStageDevice() else None,
                self._mmc.getPosition() if self._mmc.getFocusDevice() else None,
            )
        ]

        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            preview_layer.scale = (pix_size, pix_size)
        else:
            # return to default
            preview_layer.scale = [1.0, 1.0]

        self._update_max_min()

        if self.streaming_timer is None:
            self.viewer.reset_view()

    def _update_max_min(self, *_: Any) -> None:
        visible = (x for x in self.viewer.layers.selection if x.visible)
        self.minmax.update_from_layers(
            (lr for lr in visible if isinstance(lr, napari.layers.Image))
        )

    def _snap(self) -> None:
        # update in a thread so we don't freeze UI
        create_worker(self._mmc.snap, _start_thread=True)

    def _start_live(self) -> None:
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self._update_viewer)
        self.streaming_timer.start(int(self._mmc.getExposure()))

    def _stop_live(self) -> None:
        if self.streaming_timer:
            self.streaming_timer.stop()
            self.streaming_timer.deleteLater()
            self.streaming_timer = None

    def _update_live_exp(self, camera: str, exposure: float) -> None:
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

    def _mouse_right_click(
        self, viewer: napari.viewer.Viewer, event: Any
    ) -> Generator[None, None, None]:
        if not self._mmc.getXYStageDevice() and not self._mmc.getFocusDevice():
            return

        if self._mmc.getPixelSizeUm() == 0:
            return

        dragged = False
        yield
        # on move
        while event.type == "mouse_move":
            dragged = True
            yield
        if dragged:
            return
        # only right click
        if event.button != 2:
            return

        layer, viewer_coords = self._get_active_layer_and_click_coords(viewer)

        # don't open the menu if the click is not on the layer
        if layer is None or viewer_coords is None:
            return

        x, y, z = self._get_xyz_positions(layer)

        if x is None and y is None and z is None:
            return

        if x is None or y is None:
            new_pos = (x, y, z)
        else:
            new_pos = self._calculate_clicked_stage_coordinates(
                layer, viewer_coords, x, y, z
            )

        r_menu = self._create_right_click_menu(new_pos)
        r_menuPosition = self.viewer.window._qt_viewer.mapToGlobal(
            QPoint(event.pos[0], event.pos[1])
        )
        r_menu.move(r_menuPosition)
        r_menu.show()

    def _get_active_layer_and_click_coords(
        self, viewer: napari.viewer.Viewer
    ) -> tuple[napari.layers.Image | None, tuple[int, int]] | tuple[None, None]:
        # only Image layers
        layers: list[napari.layers.Image] = [
            lr
            for lr in viewer.layers.selection
            if isinstance(lr, napari.layers.Image) and lr.visible
        ]

        if not layers:
            return None, None

        viewer_coords = (
            round(viewer.cursor.position[-2]),
            round(viewer.cursor.position[-1]),
        )

        # get which layer has been clicked depending on the px value.
        # only the clicked layer has a val=value, in the other val=None
        vals = []
        layer: napari.layers.Image | None = None
        for lyr in layers:
            data_coordinates = lyr.world_to_data(viewer_coords)
            val = lyr.get_value(data_coordinates)
            vals.append(val)
            if val is not None:
                layer = lyr

        if vals.count(None) == len(layers):
            layer = None

        return layer, viewer_coords

    def _get_xyz_positions(
        self, layer: napari.layers.Image
    ) -> tuple[float | None, float | None, float | None]:
        info: list[
            tuple[tuple[int], float | None, float | None, float | None]
        ] = layer.metadata.get("positions")
        current_dispalyed_dim = list(self.viewer.dims.current_step[:-2])
        pos: tuple[float | None, float | None, float | None] = (None, None, None)
        for i in info:
            indexes, x, y, z = i
            if list(indexes) == current_dispalyed_dim or not indexes:
                pos = (x, y, z)
                break
        return pos

    def _calculate_clicked_stage_coordinates(
        self,
        layer: napari.layers.Image,
        viewer_coords: tuple[int, int],
        x: float | None,
        y: float | None,
        z: float | None,
    ) -> tuple[float, float, float | None]:
        _, _, width, height = self._mmc.getROI(self._mmc.getCameraDevice())

        # get clicked px stage coords
        top_left = layer.data_to_world((0, 0))[-2:]
        central_px = (top_left[0] + (height // 2), top_left[1] + (width // 2))

        # top left corner of image in um
        x0 = float(x - (central_px[1] * self._mmc.getPixelSizeUm()))
        y0 = float(y + (central_px[0] * self._mmc.getPixelSizeUm()))

        # viewer_coords is in um because of layer scale
        stage_x = x0 + viewer_coords[1]
        stage_y = y0 - viewer_coords[0]

        return stage_x, stage_y, z

    def _create_right_click_menu(
        self, xyz_positions: tuple[float | None, float | None, float | None]
    ) -> QMenu:
        coord_x, coord_y, coord_z = xyz_positions

        _menu = QMenu(parent=self)
        _menu.setStyleSheet(MENU_STYLE)

        if self._mmc.getXYStageDevice() and coord_x is not None and coord_y is not None:
            xy = _menu.addAction(f"Move to [x:{coord_x},  y:{coord_y}].")
            xy.triggered.connect(lambda: self._move_to_xy(xyz_positions))

        if self._mmc.getFocusDevice() and coord_z is not None:
            z = _menu.addAction(f"Move to [z:{coord_z}].")
            z.triggered.connect(lambda: self._move_to_z(xyz_positions))

        if self._mmc.getXYStageDevice() and self._mmc.getFocusDevice():
            xyz = _menu.addAction(f"Move to [x:{coord_x},  y:{coord_y},  z:{coord_z}].")
            xyz.triggered.connect(lambda: self._move_to_xyz(xyz_positions))

        if self._mda:
            to_mda = _menu.addAction("Add to MDA position table.")
            to_mda.triggered.connect(
                lambda: self._add_to_mda_position_table(xyz_positions)
            )

        return _menu

    def _move_to_xy(
        self, xyz_positions: tuple[float | None, float | None, float | None]
    ) -> None:
        x, y, _ = xyz_positions
        if x is None or y is None:
            return
        self._mmc.setXYPosition(x, y)

    def _move_to_z(
        self, xyz_positions: tuple[float | None, float | None, float | None]
    ) -> None:
        _, _, z = xyz_positions
        if z is None:
            return
        self._mmc.setPosition(z)

    def _move_to_xyz(
        self, xyz_positions: tuple[float | None, float | None, float | None]
    ) -> None:
        x, y, z = xyz_positions
        if x is None or y is None or z is None:
            return
        self._mmc.setXYPosition(x, y)
        self._mmc.setPosition(z)

    def _add_to_mda_position_table(
        self, xyz_positions: tuple[float | None, float | None, float | None]
    ) -> None:
        if not self._mda:
            return
        x, y, z = xyz_positions
        self._mda.position_widget.set_state([{"x": x, "y": y, "z": z}], clear=False)
