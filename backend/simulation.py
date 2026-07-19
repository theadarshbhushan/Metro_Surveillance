# simulation.py — Data source layer.
# Reads stations.csv and maintains the current simulation position.
# FUTURE: Replace get_current_row() to read from load-cell or YOLO — nothing else changes.

import os
import pandas as pd
from config import LOOP_AT_FINAL_STATION

# Resolve data file relative to this file's location
_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "stations.csv")


class StationSimulator:
    """
    Maintains the ordered list of stations and tracks which one we are at.
    Provides current and previous row data for movement calculation.
    """

    def __init__(self, csv_path: str = _DATA_PATH):
        self.df = pd.read_csv(csv_path)
        if self.df.empty:
            raise ValueError("stations.csv is empty.")
        self._index = 0
        self._previous_index = None  # None until first advance

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def total_stations(self) -> int:
        return len(self.df)

    @property
    def at_final_station(self) -> bool:
        return self._index == self.total_stations - 1

    def get_current_row(self) -> dict:
        return self.df.iloc[self._index].to_dict()

    def get_previous_row(self) -> dict | None:
        """Returns the previous station row, or None if we are at the start."""
        if self._previous_index is None:
            return None
        return self.df.iloc[self._previous_index].to_dict()

    def get_station_name(self, index: int) -> str | None:
        if 0 <= index < self.total_stations:
            return str(self.df.iloc[index]["Station"])
        return None

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def advance(self) -> bool:
        """
        Move to the next station.
        Returns True if advanced, False if already at final station and LOOP is off.
        """
        if self.at_final_station:
            if LOOP_AT_FINAL_STATION:
                self._previous_index = self._index
                self._index = 0
                return True
            return False  # Caller should surface at_final_station flag

        self._previous_index = self._index
        self._index += 1
        return True

    def reset(self):
        """Return to Station 1 (index 0)."""
        self._index = 0
        self._previous_index = None
