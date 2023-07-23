import numpy as np

from src.infrastructure.models import InternalModel

__all__ = ("Wave",)


class Wave(InternalModel):
    """The real wave representation."""

    height: np.float64  # unit: m
    period: np.float64  # unit: s
    angle_from_north: np.float64  # in radians, positive toward east

    @classmethod
    def from_raw(cls, payload: dict) -> "Wave":
        return cls(
            height=np.float64(payload["height"]),
            period=np.float64(payload["period"]),
            angle_from_north=np.float64(payload["angle_from_north"]),
        )
