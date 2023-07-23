import numpy as np
from numpy.typing import NDArray

from src.domain.anomaly_detection import AnomalyDetectionInDb
from src.domain.sensors import Sensor
from src.infrastructure.database.tables import SimulationDetectionRatesTable
from src.infrastructure.models import InternalModel

__all__ = (
    "CartesianCoordinates",
    "Leakage",
    "Detection",
    "SimulationDetectionRateUncommited",
    "SimulationDetectionRateInDb",
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
        return f"{self.name}({self.x},{self.y},{self.z}) [{self.rate}]"

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


class Detection(InternalModel):
    """Represents the simulation's detection payload."""

    sensor: Sensor
    leakage: Leakage
    concentrations: NDArray[np.float64]


class SimulationDetectionRateUncommited(InternalModel):
    """This model represents the payload for
    the detection rate database creation payload.
    """

    anomaly_detection_id: int
    leakage: dict
    rate: float
    # HACK: Since SQLite does not support arrays
    #       the string convestion is used
    concentrations: str


class SimulationDetectionRateInDb(InternalModel):
    """This model represents the detection rate database representation.
    It uses optimized numpy data types, leakage representation
    and nested anomaly detection model.
    """

    id: int
    anomaly_detection: AnomalyDetectionInDb
    leakage: Leakage
    rate: np.float64
    concentrations: NDArray[np.float64]

    @classmethod
    def from_orm(
        cls, schema: SimulationDetectionRatesTable
    ) -> "SimulationDetectionRateInDb":
        """Convert ORM schema representation into the internal model."""

        return cls(
            id=schema.id,
            anomaly_detection=AnomalyDetectionInDb.from_orm(
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
            rate=np.float64(schema.rate),
        )
