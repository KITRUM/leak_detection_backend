import pickle
from enum import StrEnum

from stumpy.aampi import aampi

from src.config import settings

__all__ = (
    "INITIAL_BASELINE_HIGH",
    "INITIAL_BASELINE_LOW",
    "ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE",
)


# Load initial baselines
# --------------------------------------------------------------
INITIAL_BASELINE_HIGH: aampi = pickle.load(
    open(f"{settings.seed_dir}/baselines/high.mpstream", "rb")
)
INITIAL_BASELINE_LOW: aampi = pickle.load(
    open(f"{settings.seed_dir}/baselines/low.mpstream", "rb")
)


# Load initial baselines
# --------------------------------------------------------------
class CacheNamespace(StrEnum):
    interactive_mode_turned_on = "interactive_mode_turned_on"


# Error messages
# --------------------------------------------------------------
ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE = (
    "Anomaly detection processing is skipped "
    "due to not enough elements in the matrix profile. "
    "Current amount: {matrix_profile_counter}"
)
