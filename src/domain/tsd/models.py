from datetime import datetime

import numpy as np
from pydantic import BaseModel, validator

from src.domain.sensors import SensorInDb
from src.infrastructure.models import InternalModel

__all__ = ("TsdRaw", "TsdUncommited", "TsdInDb", "Tsd")


class TsdRaw(BaseModel):
    """The raw representation of time series data.
    This data model is used as a intermediate model by parser.
    """

    ppmv: float
    timestamp: datetime


class TsdUncommited(TsdRaw, InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    ppmv: np.float64
    sensor_id: int

    def __str__(self) -> str:
        return f"🕑 TSD: {self.timestamp} [{self.ppmv} ppmv]"


class TsdInDb(TsdUncommited):
    """The internal representation of the existed Time Series Data."""

    id: int

    @validator("ppmv", pre=True)
    def convert_ppmv(cls, value: float | np.float64) -> np.float32:
        if type(value) == np.float64:
            return value

        return np.float64(value)


class Tsd(TsdRaw, InternalModel):
    """The internal representation of reach Time Series Data."""

    id: int
    ppmv: np.float64
    sensor: SensorInDb

    @validator("ppmv", pre=True)
    def convert_ppmv(cls, value: float | np.float64) -> np.float32:
        if type(value) == np.float64:
            return value

        return np.float64(value)
