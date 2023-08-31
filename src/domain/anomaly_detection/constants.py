from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

__all__ = ("ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE",)


class CacheNamespace(StrEnum):
    interactive_mode_turned_on = "interactive_mode_turned_on"


# Error messages
# --------------------------------------------------------------
ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE = (
    "Anomaly detection processing is skipped "
    "due to not enough elements in the matrix profile. "
    "Current amount: {matrix_profile_counter}"
)

SEED_BASELINES_STATS_BY_FILENAME: dict[str, NDArray[np.float64]] = {
    "mp_low.mpstream": np.array(
        [
            np.float64("23.92166052509913"),
            np.float64("115.11018472633732"),
        ]
    ),
    "mp_mid.mpstream": np.array(
        [
            np.float64("33.70430007737835"),
            np.float64("742.793525496084"),
        ]
    ),
    "mp_high.mpstream": np.array(
        [
            np.float64("37.95233682018488"),
            np.float64("1808.526258299781"),
        ]
    ),
    "mp_trestakk1ta.mpstream": np.array(
        [
            np.float64("26.716740813215797"),
            np.float64("261.18723326385407"),
        ]
    ),
}
