import json
from pathlib import Path
from typing import Any

import zarr
from useq import MDASequence
from zarr import Array


class TensorZarrReader:
    def __init__(self, path: str | Path):
        self._path = path

        # open the zarr file
        self._zarr: Array = zarr.open(self._path)

    @property
    def path(self) -> Path:
        """Return the path."""
        return Path(self._path)

    @property
    def zarr(self) -> Array:
        """Return the zarr file."""
        return self._zarr

    @property
    def sequence(self) -> MDASequence | None:
        """Return the MDASequence."""
        try:
            return MDASequence(**json.loads(self._zarr.attrs["useq_MDASequence"]))
        except KeyError:
            return None

    def _create_axis_tuple(self, axis: str) -> int:
        """Create a tuple with the correct slice for the given axis."""
        if self.sequence is None:
            raise ValueError("No sequence found in the metadata.")

        if axis not in self.sequence.axis_order:
            raise ValueError(f"Axis {axis} not found in the MDASequence")

        return self.sequence.axis_order.index(axis)

    def get_axis_data(self, axis_and_index: dict[str, int]) -> Array:
        """Return the data for the given axis.

        NOTE: Only one axis is allowed, e.g. {'p': 1}
        """
        if len(axis_and_index.keys()) != 1:
            raise ValueError("Only one axis is allowed, e.g. {'p': 1}!")

        # get axis and index (e.g. axis_and_index = {"p": 1} -> axis = "p", index = 1)
        (axis,), (index,) = axis_and_index.keys(), axis_and_index.values()
        # get the correct tuple for the axis (e.g. axis_index = 1)
        axis_index = self._create_axis_tuple(axis)
        # get the correct tuple for the axis
        # e.g. axis_tuple = [slice(None), 1, slice(None), slice(None)]
        axis_tuple = [
            slice(None) if i != axis_index else 0 for i in range(len(self.zarr.shape))
        ]
        # update the axis_tuple with the requested index in the correct position
        axis_tuple[axis_index] = index
        # return the data for the given axis
        return self.zarr[tuple(axis_tuple)]

    def get_axis_data_and_metadata(
        self, axis_and_index: dict[str, int]
    ) -> tuple[Array, list[dict[str, Any]]]:
        """Return the data for the given axis and its metadata.

        NOTE: Only one axis is allowed, e.g. {'p': 1}
        """
        data = self.get_axis_data(axis_and_index)

        meta = self.zarr.attrs.get("frame_metadatas")
        if meta is None:
            return self.get_axis_data(axis_and_index), []

        axis_meta = []
        (axis,), (index,) = axis_and_index.keys(), axis_and_index.values()
        for i in self.zarr.attrs["frame_metadatas"]:
            event = i["Event"]
            event_index = event["index"]
            if axis in event_index and index == event_index.get(axis):
                axis_meta.append(i)

        return data, axis_meta
