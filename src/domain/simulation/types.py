from typing import Protocol

import numpy as np

from src.domain.currents import Current
from src.domain.sensors import Sensor

from .models import CartesianCoordinates, Leakage

__all__ = ("RegressionProcessor",)


# This type corresponds to the detection rate processor
# that is used as a callback by regressions.
class RegressionProcessor(Protocol):
    def __call__(
        self,
        sensor: Sensor,
        leakage: Leakage,
        current: Current,
        coordinates: CartesianCoordinates,
        Cd: np.float64,
    ) -> np.float64:
        ...
