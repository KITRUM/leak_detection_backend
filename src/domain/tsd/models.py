from datetime import datetime

import numpy as np
from pydantic import validator

from src.domain.sensors import Sensor
from src.infrastructure.models import InternalModel

__all__ = ("TsdRaw", "TsdUncommited", "TsdFlat", "Tsd")


def _convert_ppmv_to_internal_callback(
    cls, value: float | np.float64
) -> np.float64:
    """The validation callback that is used by Pydantic."""

    if type(value) == np.float64:
        return value
    return np.float64(value)


class TsdRaw(InternalModel):
    """The raw representation of time series data.
    This data model is used as a intermediate model by parser.
    """

    ppmv: float
    timestamp: datetime


class TsdUncommited(InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    ppmv: np.float64
    timestamp: datetime
    sensor_id: int

    def __str__(self) -> str:
        return f"🕑 TSD: {self.timestamp} [{self.ppmv} ppmv]"


class TsdFlat(TsdUncommited):
    """The internal representation of the existed Time Series Data."""

    id: int

    validator("ppmv", pre=True, allow_reuse=True)(
        _convert_ppmv_to_internal_callback
    )


class Tsd(TsdFlat):
    """The internal representation of reach Time Series Data."""

    sensor: Sensor

    validator("ppmv", pre=True, allow_reuse=True)(
        _convert_ppmv_to_internal_callback
    )
