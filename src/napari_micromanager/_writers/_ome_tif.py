from __future__ import annotations

import json
from pathlib import Path

from pymmcore_plus.mda.handlers import OMETiffWriter

META = "_metadata.json"


class OMETifWriter(OMETiffWriter):
    """MDA handler that writes to a 5D OME-TIFF file.

    Positions will be split into different files.

    Data is memory-mapped to disk using numpy.memmap via tifffile.  Tifffile handles
    the OME-TIFF format.

    Parameters
    ----------
    filename : Path | str
        The filename to write to.  Must end with '.ome.tiff' or '.ome.tif'.
    """

    def __init__(self, filename: Path | str) -> None:
        super().__init__(filename)

    def finalize_metadata(self) -> None:
        """Write the metadata per position to a json file.

        This method is called when the 'sequenceFinished' signal is received.
        """
        if not self._is_ome:
            return
        ext = ".ome.tif" if self._is_ome else ".tif"
        for position_key in reversed(list(self.frame_metadatas.keys())):
            base_path = self._filename.replace(ext, f"_{position_key}")
            meta = {f"{Path(base_path).name}{ext}": self.frame_metadatas[position_key]}
            with open(base_path + META, "w") as f:
                formatted = json.dumps(meta, indent=2)
                f.write(formatted)
