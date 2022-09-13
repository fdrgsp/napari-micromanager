from loguru import logger
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import MDAEngine
from useq import MDASequence


class FindWells(MDAEngine):
    """An engine to find wells contiining only 2 cells."""

    def __init__(self, mmc: CMMCorePlus = None) -> None:
        super().__init__(mmc)

        self._mmc = mmc

    def run(self, sequence: MDASequence) -> None:
        """An engine to find wells contiining only 2 cells."""
        self._prepare_to_run(sequence)

        for event in sequence:
            cancelled = self._wait_until_event(event, sequence)

            # If cancelled break out of the loop
            if cancelled:
                break

            logger.info(event)
            self._prep_hardware(event)

            logger.info(event.pos_name)

            # self._mmc.snapImage()
            # img = self._mmc.getImage()

            # self._events.frameReady.emit(img, event)
        self._finish_run(sequence)
