import numpy as np
from numpy.typing import NDArray

from src.domain.anomaly_detection import AnomalyDetectionFlat
from src.infrastructure.database import SimulationDetectionsTable
from src.infrastructure.models import InternalModel

__all__ = (
    "CartesianCoordinates",
    "Leakage",
    "DetectionUncommited",
    "Detection",
)


class CartesianCoordinates(InternalModel):
    """Used for the simulation processing as
    a sensor's transformed coordinates.
    """

    x: np.float64
    y: np.float64


class Leakage(InternalModel):
    """Represents the leakage in the simulation."""

    name: str
    rate: np.float64  # unit: kg/s
    x: np.float64  # unit: m
    y: np.float64  # unit: m
    z: np.float64  # unit: m
    duration: np.float64  # unit: s

    def __str__(self) -> str:
        return f"{self.name}({self.x},{self.y},{self.z})"

    @classmethod
    def from_raw(cls, payload: dict) -> "Leakage":
        return cls(
            name=payload["name"],
            rate=np.float64(payload["rate"]),
            x=np.float64(payload["x"]),
            y=np.float64(payload["y"]),
            z=np.float64(payload["z"]),
            duration=np.float64(payload["duration"]),
        )


class DetectionUncommited(InternalModel):
    """Represents the simulation's detection payload."""

    anomaly_detection_id: int
    leakage: dict
    # HACK: Since SQLite does not support arrays
    #       the string convestion is used
    concentrations: str


class Detection(InternalModel):
    """This model represents the detection database representation."""

    anomaly_detection: AnomalyDetectionFlat
    leakage: Leakage
    concentrations: NDArray[np.float64]
    id: int

    @classmethod
    def from_orm(cls, schema: SimulationDetectionsTable) -> "Detection":
        """Convert ORM schema representation into the internal model."""

        return cls(
            id=schema.id,
            anomaly_detection=AnomalyDetectionFlat.from_orm(
                schema.anomaly_detection
            ),
            leakage=Leakage(
                name=schema.leakage["name"],
                rate=np.float64(schema.leakage["rate"]),
                duration=np.float64(schema.leakage["duration"]),
                x=np.float64(schema.leakage["x"]),
                y=np.float64(schema.leakage["y"]),
                z=np.float64(schema.leakage["z"]),
            ),
            concentrations=np.array(
                schema.concentrations.split(","), dtype=np.float64
            ),
        )
