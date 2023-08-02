from copy import deepcopy

import numpy as np
from loguru import logger
from sqlalchemy import delete
from stumpy.aampi import aampi

from src.domain.tsd import Tsd
from src.infrastructure.database import AnomalyDetectionsTable
from src.infrastructure.database.services.transaction import transaction

from .constants import INITIAL_BASELINE_HIGH, INITIAL_BASELINE_LOW
from .feedback_mode_processor import sensor_stream
from .models import (
    AnomalyDetection,
    AnomalyDetectionUncommited,
    AnomalyDeviation,
    MatrixProfile,
    MatrixProfileLevel,
)
from .repository import AnomalyDetectionRepository

# Temporary variable
# TODO: Should be changed to the database later.
MATRIX_PROFILES: dict[int, MatrixProfile] = {}


@transaction
async def save_anomaly_detection(
    schema: AnomalyDetectionUncommited,
) -> AnomalyDetection:
    repository = AnomalyDetectionRepository()
    instance = await repository.create(schema)

    return await repository.get(instance.id)


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await AnomalyDetectionRepository().execute(delete(AnomalyDetectionsTable))


@transaction
async def get_historical_data(
    sensor_id: int,
) -> list[AnomalyDetection]:
    """Get the historical data."""

    return [
        instance
        async for instance in AnomalyDetectionRepository().by_sensor(sensor_id)
    ]


def copy_initial_baseline(
    level: MatrixProfileLevel = MatrixProfileLevel.HIGH,
) -> aampi:
    """Get a deepcopy of the initial baseline."""

    match level:
        case MatrixProfileLevel.HIGH:
            baseline = deepcopy(INITIAL_BASELINE_HIGH)
        case MatrixProfileLevel.LOW:
            baseline = deepcopy(INITIAL_BASELINE_LOW)
        case _:
            raise Exception("Unknown baseline profile leve")

    return baseline


def update_matrix_profile(matrix_profile: MatrixProfile, tsd: Tsd) -> None:
    """Update the matrix profile with the new data."""

    if matrix_profile.counter >= (matrix_profile.window * 2):
        # Reset the matrix profile baseline and last values
        matrix_profile.counter = 0
        matrix_profile.baseline = copy_initial_baseline(
            matrix_profile.mp_level
        )
        matrix_profile.last_values = matrix_profile.last_values[
            -matrix_profile.window :
        ]
        for value in matrix_profile.last_values:
            matrix_profile.baseline.update(value)

    matrix_profile.baseline.update(tsd.ppmv)
    matrix_profile.counter += 1
    matrix_profile.last_values.append(tsd.ppmv)


def feedback_mode_processing(tsd: Tsd) -> AnomalyDetectionUncommited:
    pass


def process(tsd: Tsd) -> AnomalyDetectionUncommited:
    """The main anomaly detection processing entrypoint."""

    if not (matrix_profile := MATRIX_PROFILES.get(tsd.sensor.id)):
        # Create default matrix profile if not exist
        logger.success("Create the matrix profile")
        baseline = copy_initial_baseline(level=MatrixProfileLevel.HIGH)
        matrix_profile = MatrixProfile(
            max_dis=np.float64(max(baseline.P_)),
            baseline=baseline,
        )
        MATRIX_PROFILES[tsd.sensor.id] = matrix_profile

    # Update the matrix profile with new Time series data
    update_matrix_profile(matrix_profile, tsd)

    dis = matrix_profile.baseline.P_[-1:]
    dis_lvl = dis / matrix_profile.max_dis * 100

    if dis_lvl < matrix_profile.warning:
        deviation = AnomalyDeviation.OK
    elif dis_lvl >= matrix_profile.warning and dis_lvl < matrix_profile.alert:
        deviation = AnomalyDeviation.WARNING
    else:
        deviation = AnomalyDeviation.CRITICAL

    create_schema = AnomalyDetectionUncommited(
        value=deviation, time_series_data_id=tsd.id
    )

    return create_schema
