from enum import StrEnum, auto

__all__ = ("AnomalyDeviation",)


class AnomalyDeviation(StrEnum):
    CRITICAL = auto()
    WARNING = auto()
    OK = auto()
