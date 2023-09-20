"""
This module includes services for the initial baseline does the augmentation.
"""

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from stumpy import aampi

from src.domain.sensors import Sensor

__all__ = ("initial_baseline_augment",)


async def initial_baseline_augment(
    sensor: Sensor, cleaned_concentrations: NDArray[np.float64]
) -> aampi:
    """Takes the cleaned concentrations data from all historical data
    for the specific sensor and update the baseline in the database.
    """

    logger.success(
        f"Updating the initial baseline for the sensor {sensor.name}."
    )

    sensor_baseline: aampi = (
        sensor.configuration.anomaly_detection_initial_baseline
    )

    for concentration in cleaned_concentrations:
        sensor_baseline.update(concentration)

    return sensor_baseline
