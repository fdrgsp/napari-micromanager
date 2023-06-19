import contextlib
from typing import Any

from pymmcore_plus import CMMCorePlus
from pymmcore_plus._logger import logger
from pymmcore_plus.mda import PMDAEngine
from useq import MDAEvent, MDASequence


class FastTimeSequence(PMDAEngine):
    """Fast sequence engine.

    Used only if the sequence is a timelapse with 0 interval, a single channel,
    no z_plan (but single z) and no grid_plan. It can have multiple positions
    with or without autofocus.
    """

    def __init__(self, mmc: CMMCorePlus) -> None:
        self._mmc = mmc

    def setup_sequence(self, sequence: MDASequence) -> None:
        """Setup the hardware for the fast sequence."""
        self._mmc = self._mmc or CMMCorePlus.instance()

    def setup_event(self, event: MDAEvent) -> None:
        """Set the system hardware.

        Only executed if t=0.

        Parameters
        ----------
        event : MDAEvent
            The event to use for the Hardware config
        """
        if event.index["t"] != 0:
            return

        if event.channel is not None:
            self._mmc.setConfig(event.channel.group, event.channel.config)

        if event.exposure is not None:
            self._mmc.setExposure(event.exposure)

        if event.x_pos is not None or event.y_pos is not None:
            x = event.x_pos if event.x_pos is not None else self._mmc.getXPosition()
            y = event.y_pos if event.y_pos is not None else self._mmc.getYPosition()
            self._mmc.setXYPosition(x, y)

        if event.z_pos is not None:
            if event.autofocus is None:  # type: ignore
                self._mmc.setZPosition(event.z_pos)
            else:
                z_af_device, z_af_pos = event.autofocus  # type: ignore
                z_after_af = self._execute_autofocus(z_af_device, z_af_pos)
                self._mmc.setZPosition(z_after_af)

                # TODO: maybe here we want to set the autofocus engaged and locked
                # so it will stay on for the rest of the sequence. If so, maybe we need
                # disable it before running self._execute_autofocus(...).

        self._mmc.waitForSystem()

    def _execute_autofocus(self, z_af_device_name: str, z_af_pos: float) -> float:
        """Perform the autofocus."""
        self._mmc.setPosition(z_af_device_name, z_af_pos)
        self._mmc.fullFocus()
        return self._mmc.getZPosition()

    def exec_event(self, event: MDAEvent) -> Any:
        """Execute the event.

        Only executed if t=0.
        """
        if event.index["t"] != 0:
            # if t > 0, we can stop the sequence since it has been already
            # executed by 'startSequenceAcquisition'.
            self._mmc.mda._running = False
            return

        images = len(event.sequence.time_plan)  # type: ignore

        data_indexes: list[int] = []

        self._mmc.startSequenceAcquisition(images, 0, True)
        while self._mmc.isSequenceRunning():
            if cancelled := self._mmc.mda._check_canceled():
                self._mmc.mda.cancel()
                self._mmc.stopSequenceAcquisition()

            with contextlib.suppress(IndexError):
                img = self._mmc.popNextImageAndMD()
                img_idx = int(img[1]["ImageNumber"])
                if img_idx in data_indexes:
                    continue
                self._mmc.mda.events.frameReady.emit(
                    img[0], self._update_event(event, img_idx)
                )
                logger.info(
                    f"event: {self._update_event(event, img_idx)},"
                    f"image n: {img_idx}, "
                    f"elapsed_time: {img[1]['ElapsedTime-ms']}"
                )
                data_indexes.append(img_idx)

        self._mmc.stopSequenceAcquisition()

        if img_idx < images and not cancelled:
            for n, idx in enumerate(range(img_idx + 1, images)):
                img = self._mmc.getNBeforeLastImageAndMD(n)
                self._mmc.mda.events.frameReady.emit(
                    img[0], self._update_event(event, idx)
                )
                logger.info(
                    f"event: {self._update_event(event, idx)},"
                    f"image n: {idx}, "
                    f"elapsed_time: {img[1]['ElapsedTime-ms']}"
                )
                data_indexes.append(idx)

        if len(data_indexes) != images and not cancelled:
            raise RuntimeError(f"Expected {images} images, got {len(data_indexes)}.")

    def _update_event(self, event: MDAEvent, img_idx: int) -> MDAEvent:
        update = {"index": {"c": event.index["c"], "t": img_idx, "p": event.index["p"]}}
        return event.copy(update=update)
