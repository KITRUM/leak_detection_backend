from enum import StrEnum

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
