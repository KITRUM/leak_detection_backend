import numpy as np
from numpy.typing import NDArray

from src.domain.sensors import Sensor
from src.infrastructure.database.tables import SimulationDetectionRatesTable
from src.infrastructure.models import InternalModel

__all__ = (
    "CartesianCoordinates",
    "Leakage",
    "SimulationDetectionRate",
    "SimulationDetectionRateUncommited",
    "SimulationDetectionRateInDb",
)


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


class SimulationDetectionRate(InternalModel):
    """Represents the simulation's detection payload."""

    sensor: Sensor
    leakage: Leakage
    concentrations: NDArray[np.float32]


class SimulationDetectionRateUncommited(InternalModel):
    anomaly_detection_id: int
    leakage: dict
    rate: float
    # HACK: Since SQLite does not support arrays
    #       the string convestion is used
    concentrations: str


class SimulationDetectionRateInDb(SimulationDetectionRateUncommited):
    id: int
    leakage: Leakage
    rate: np.float32
    concentrations: NDArray[np.float32]

    @classmethod
    def from_orm(
        cls, schema: SimulationDetectionRatesTable
    ) -> "SimulationDetectionRateInDb":
        """Convert ORM schema representation into the internal model."""

        return cls(
            id=schema.id,
            anomaly_detection_id=schema.anomaly_detection_id,
            leakage=Leakage(
                name=schema.leakage["name"],
                rate=np.float32(schema.leakage["rate"]),
                duration=np.float32(schema.leakage["duration"]),
                x=np.float32(schema.leakage["x"]),
                y=np.float32(schema.leakage["y"]),
                z=np.float32(schema.leakage["z"]),
            ),
            concentrations=np.array(
                schema.concentrations.split(","), dtype=np.float32
            ),
            rate=np.float32(schema.rate),
        )
