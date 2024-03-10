from __future__ import annotations

from typing import TYPE_CHECKING

from pyfirmata2 import Arduino
from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from typing import TypedDict

    from pyfirmata2.pyfirmata2 import Pin

    class StimulationValues(TypedDict):
        arduino_led: Pin
        led_pulse_duration: float
        frames: dict[int, int]


FIXED = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
PIN = "d:3:p"
LABEL_MAX_SIZE = 300


class ArduinoLedControl(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Arduino LED Control")

        self._arduino_board: Arduino = None
        self._led_on_frames: list[int] = []
        self._led_pin: Pin | None = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # GROUP - to detect the arduino board
        detect_board = QGroupBox("Arduino Board")
        port_lbl = QLabel("Arduino Port:")
        port_lbl.setSizePolicy(FIXED)
        self._board_com = QLineEdit()
        self._board_com.setPlaceholderText("Autodetect")
        self._detect_btn = QPushButton("Detect")
        self._detect_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._detect_btn.setToolTip("Click to detect the board. If no ")
        self._detect_btn.clicked.connect(self._detect_arduino_board)
        _board_label = QLabel("Arduino Board:")
        self._board_name = QLabel()
        # layout
        detect_gp_layout = QGridLayout(detect_board)
        detect_gp_layout.setContentsMargins(10, 10, 10, 10)
        detect_gp_layout.setSpacing(10)
        detect_gp_layout.addWidget(port_lbl, 0, 0)
        detect_gp_layout.addWidget(self._board_com, 0, 1)
        detect_gp_layout.addWidget(self._detect_btn, 0, 2)
        detect_gp_layout.addWidget(_board_label, 1, 0)
        detect_gp_layout.addWidget(self._board_name, 1, 1, 1, 2)

        # GROUP - to set on which frames to turn on the LED
        frame_group = QGroupBox("Stimulation Frames")
        # initial delay
        initial_delay_lbl = QLabel("Initial Delay:")
        initial_delay_lbl.setSizePolicy(FIXED)
        self._initial_delay_spin = QSpinBox()
        self._initial_delay_spin.setRange(0, 100000)
        self._initial_delay_spin.setSuffix(" frames")
        self._initial_delay_spin.valueChanged.connect(self.frame_values_changed)
        # interval
        interval_lbl = QLabel("Interval:")
        initial_delay_lbl.setSizePolicy(FIXED)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(0, 100000)
        self._interval_spin.setSuffix(" frames")
        self._interval_spin.valueChanged.connect(self.frame_values_changed)
        # number of pulses
        num_pulses_lbl = QLabel("Number of Pulses:")
        num_pulses_lbl.setSizePolicy(FIXED)
        self._num_pulses_spin = QSpinBox()
        self._num_pulses_spin.setRange(0, 100000)
        self._num_pulses_spin.valueChanged.connect(self.frame_values_changed)
        # separator
        separator = _SeparatorWidget()
        # total number of frames
        total_frames_lbl = QLabel("Total Frames:")
        self._total_frames = QLabel()
        # pulse after frame indicator
        pulse_after_frame_lbl = QLabel("Pulse After Frame:")
        self._pulse_after_frame = QLabel()
        self._pulse_after_frame.setMaximumWidth(LABEL_MAX_SIZE)
        # layout
        frame_gp_layout = QGridLayout(frame_group)
        frame_gp_layout.setContentsMargins(10, 10, 10, 10)
        frame_gp_layout.setSpacing(10)
        frame_gp_layout.addWidget(initial_delay_lbl, 0, 0)
        frame_gp_layout.addWidget(self._initial_delay_spin, 0, 1)
        frame_gp_layout.addWidget(interval_lbl, 1, 0)
        frame_gp_layout.addWidget(self._interval_spin, 1, 1)
        frame_gp_layout.addWidget(num_pulses_lbl, 2, 0)
        frame_gp_layout.addWidget(self._num_pulses_spin, 2, 1)
        frame_gp_layout.addWidget(separator, 3, 0, 1, 2)
        frame_gp_layout.addWidget(total_frames_lbl, 4, 0)
        frame_gp_layout.addWidget(self._total_frames, 4, 1)
        frame_gp_layout.addWidget(pulse_after_frame_lbl, 5, 0)
        frame_gp_layout.addWidget(self._pulse_after_frame, 5, 1)

        # GROUP - to set the led power
        led_group = QGroupBox("LED")
        # start power
        led_start_pwr_lbl = QLabel("Start Power")
        led_start_pwr_lbl.setSizePolicy(FIXED)
        self._led_start_power = QSpinBox()
        self._led_start_power.setRange(0, 100)
        self._led_start_power.setSuffix(" %")
        # power increment
        led_power_increment_lbl = QLabel("Power Increment:")
        led_power_increment_lbl.setSizePolicy(FIXED)
        self._led_power_increment = QSpinBox()
        self._led_power_increment.setRange(0, 100)
        self._led_power_increment.setSuffix(" %")
        # pulse duration
        pulse_duration_lbl = QLabel("Pulse Duration:")
        pulse_duration_lbl.setSizePolicy(FIXED)
        self._pulse_duration_spin = QSpinBox()
        self._pulse_duration_spin.setRange(0, 100000)
        self._pulse_duration_spin.setSuffix(" ms")
        # separator
        separator = _SeparatorWidget()
        # led info
        self._led_pwrs_lbl = QLabel("Power(s):")
        self._led_pwrs_lbl.setMaximumWidth(500)
        self_led_max_pwr_warning_lbl = QLabel()
        self_led_max_pwr_warning_lbl.hide()
        # layout
        led_gp_layout = QGridLayout(led_group)
        led_gp_layout.setContentsMargins(10, 10, 10, 10)
        led_gp_layout.setSpacing(10)
        led_gp_layout.addWidget(led_start_pwr_lbl, 0, 0)
        led_gp_layout.addWidget(self._led_start_power, 0, 1)
        led_gp_layout.addWidget(led_power_increment_lbl, 1, 0)
        led_gp_layout.addWidget(self._led_power_increment, 1, 1)
        led_gp_layout.addWidget(pulse_duration_lbl, 2, 0)
        led_gp_layout.addWidget(self._pulse_duration_spin, 2, 1)
        led_gp_layout.addWidget(separator, 3, 0, 1, 2)
        led_gp_layout.addWidget(self._led_pwrs_lbl, 4, 0)
        led_gp_layout.addWidget(self_led_max_pwr_warning_lbl, 4, 1)

        # button box (using QPushButton instead of QDialogButtonBox to avoid the focus)
        ok_btn = QPushButton("OK")
        ok_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        # layout
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btns_layout.addWidget(cancel_btn)
        btns_layout.addWidget(ok_btn)

        # add all the widgets to the main layout
        main_layout.addWidget(detect_board)
        main_layout.addWidget(frame_group)
        main_layout.addWidget(led_group)
        main_layout.addLayout(btns_layout)

        # set the fixed size for the labels
        for lbl in [
            port_lbl,
            led_start_pwr_lbl,
            led_power_increment_lbl,
            pulse_duration_lbl,
            initial_delay_lbl,
            interval_lbl,
            num_pulses_lbl,
        ]:
            lbl.setFixedSize(num_pulses_lbl.minimumSizeHint())

        # set the fixed height for the dialog
        self.setFixedHeight(self.minimumSizeHint().height())

    def value(self) -> StimulationValues:
        """Return the values set in the dialog."""
        return {
            "arduino_led": self._led_pin,
            "led_pulse_duration": self._pulse_duration_spin.value(),
            "frames": {},
        }

    def _detect_arduino_board(self) -> None:
        """Detect the Arduino board and update the GUI."""
        # if the port is empty, try to autodetect the board
        if not self._board_com.text():
            try:
                self._arduino_board = Arduino(Arduino.AUTODETECT)
                self._update_arduino_board_info()
            except Exception:
                return self._show_critical_messagebox(
                    "Unable to Autodetect the Arduino Board. \nPlease insert the port "
                    "manually in the 'Arduino Port' field."
                )
        # if the port is specified, try to detect the board on the specified port
        else:
            try:
                self._arduino_board = Arduino(self._board_com.text())
                self._update_arduino_board_info()
            except Exception:
                return self._show_critical_messagebox(
                    "Unable to detect the Arduino Board on the specified port."
                )

    def _update_arduino_board_info(self) -> None:
        """Update the GUI with the detected Arduino board info."""
        self._led_pin = self._arduino_board.get_pin(PIN)
        self._board_name.setText(self._arduino_board.name)
        # str(self._arduino_board) -> "Board{0.name} on {0.sp.port}".format(self)
        port = str(self._arduino_board).split("on")[-1].replace(" ", "")
        self._board_com.setText(port)

    def _show_critical_messagebox(self, message: str) -> None:
        """Show a critical message box with the given message."""
        self._arduino_board = None
        self._led_pin = None
        self._board_name.setText("")
        self._board_com.clear()
        QMessageBox.critical(
            self, "Arduino Board Detection Failed", message, buttons=QMessageBox.Ok
        )
        return

    def frame_values_changed(self) -> None:
        """Update the frame info and set the led_on_frames."""
        self._led_on_frames.clear()

        if not self._num_pulses_spin.value():
            return

        total_frames = (
            self._initial_delay_spin.value()
            + ((self._interval_spin.value() or 1) * self._num_pulses_spin.value())
        ) - self._num_pulses_spin.value()
        self._total_frames.setText(str(total_frames))

        fr = self._initial_delay_spin.value()
        for _ in range(self._num_pulses_spin.value()):
            self._led_on_frames.append(fr)
            # Add 1 to account for the duration of the pulse
            fr += self._interval_spin.value() + 1

        frames_stim = (
            [str(f - 1) for f in self._led_on_frames]
            if self._interval_spin.value() > 0
            else "N/A"
        )
        self._pulse_after_frame.setText(f"{frames_stim}")
        self._pulse_after_frame.setToolTip(f"{frames_stim}")

        print()
        print(self._led_on_frames)

    # def led_values_changed(self):
    #     led_power_used = []
    #     pwr = self._led_start_power.value()
    #     for _ in range (self._pulse_duration_spin.value()):
    #         led_power_used.append(pwr)
    #         pwr = pwr + self._led_power_increment.value()

    #     self.led_pwrs_label.setText(str(led_power_used))

    #     power_max = (self.led_start_pwr_spinBox.value()+
    # (self.led_pwr_inc_spinBox.value()*(self.Pulses_spinBox.value()-1)))
    #     self.led_max_pwr_label.setText(str(power_max))

    #     if power_max > 100:
    #         self.LED_on_Button.setEnabled(False)
    #         self.led_max_pwr_label.setText('LED max power exceeded!!!')
    #     else:
    #         self.LED_on_Button.setEnabled(True)
    #         self.led_max_pwr_label.setText(str(power_max))

    #     led_power_used.clear()


class _SeparatorWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.SolidLine))
        painter.drawLine(self.rect().topLeft(), self.rect().topRight())


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])

    win = ArduinoLedControl()
    win.show()

    app.exec()

# try:
#     PORT =  Arduino.AUTODETECT
#     board = Arduino(PORT)
# except Exception:
#     board = Arduino('COM4')

# led = board.get_pin('d:3:p')
