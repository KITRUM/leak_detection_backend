import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from src.domain.sensors import Sensor
from src.infrastructure.models import InternalModel

__all__ = ("CartesianCoordinates", "Leakage", "DetectionRate")


class CartesianCoordinates(InternalModel):
    """Used for the simulation processing as
    a sensor's transformed coordinates.
    """
    x: np.float32
    y: np.float32


class Leakage(InternalModel):
    """Represents the leakage in the simulation."""

    name: str
    rate: np.float32  # unit: kg/s
    x: np.float32  # unit: m
    y: np.float32  # unit: m
    z: np.float32  # unit: m
    duration: np.float32  # unit: s

    def __str__(self) -> str:
        return f"{self.name}({self.x},{self.y},{self.z}) [{self.rate}]"

    @classmethod
    def from_raw(cls, payload: dict) -> "Leakage":
        return cls(
            name=payload["name"],
            rate=np.float32(payload["rate"]),
            x=np.float32(payload["x"]),
            y=np.float32(payload["y"]),
            z=np.float32(payload["z"]),
            duration=np.float32(payload["duration"]),
        )


class DetectionRate(InternalModel):
    """Represents the simulation's result."""

    sensor: Sensor
    leakage: Leakage
    concentrations: list[np.float32] = Field(default_factory=list)

    # Only for closed template
    equilibrium_concentration: list[np.float32] = Field(default_factory=list)
