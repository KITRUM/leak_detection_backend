from copy import deepcopy

import numpy as np
from loguru import logger
from sqlalchemy import delete
from stumpy.aampi import aampi

from src.config import settings
from src.domain.tsd import Tsd
from src.infrastructure.cache import Cache
from src.infrastructure.database import AnomalyDetectionsTable
from src.infrastructure.database.services.transaction import transaction
from src.infrastructure.errors import (
    AnomalyDetectionMatrixProfileError,
    NotFoundError,
)

from .constants import (
    INITIAL_BASELINE_HIGH,
    INITIAL_BASELINE_LOW,
    CacheNamespace,
)
from .models import (
    AnomalyDetection,
    AnomalyDetectionUncommited,
    AnomalyDeviation,
    MatrixProfile,
    MatrixProfileLevel,
)
from .repository import AnomalyDetectionRepository

# TODO: Should be moved to the infrastructure later.
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


# ************************************************
# ********** Processing **********
# ************************************************
def interactive_feedback_mode_processing(
    matrix_profile: MatrixProfile, tsd: Tsd
) -> AnomalyDetectionUncommited:
    """The interactive feedback mode processing implementation.
    It is used in case the sensor.configuration.interactive_feedback_mode
    is turned on.
    """

    matrix_profile.baseline.update(tsd.ppmv)
    matrix_profile.last_values.append(tsd.ppmv)
    matrix_profile.counter += 1

    # The processing is skipped if not enough items in the matrix profile
    if matrix_profile.counter < settings.anomaly_detection.window_size:
        raise AnomalyDetectionMatrixProfileError(matrix_profile.counter)

    dis = matrix_profile.fb_baseline.P_[-1:]
    dis_lvl = dis / matrix_profile.fb_max_dis * 100

    # Compare the distance with the edge value from matrix profile
    if dis_lvl < matrix_profile.warning:
        deviation = AnomalyDeviation.OK
    elif dis_lvl >= matrix_profile.warning and dis_lvl < matrix_profile.alert:
        deviation = AnomalyDeviation.WARNING
    else:
        deviation = AnomalyDeviation.CRITICAL

    return AnomalyDetectionUncommited(
        value=deviation,
        time_series_data_id=tsd.id,
        interactive_feedback_mode=True,
    )


def normal_mode_processing(
    matrix_profile: MatrixProfile, tsd: Tsd
) -> AnomalyDetectionUncommited:
    """The regular/normal mode for the anomaly detection process."""

    update_matrix_profile(matrix_profile, tsd)

    # The processing is skipped if not enough items in the matrix profile
    if matrix_profile.counter < settings.anomaly_detection.window_size:
        raise AnomalyDetectionMatrixProfileError(matrix_profile.counter)

    dis = matrix_profile.baseline.P_[-1:]
    dis_lvl = dis / matrix_profile.max_dis * 100

    if dis_lvl < matrix_profile.warning:
        deviation = AnomalyDeviation.OK
    elif dis_lvl >= matrix_profile.warning and dis_lvl < matrix_profile.alert:
        deviation = AnomalyDeviation.WARNING
    else:
        deviation = AnomalyDeviation.CRITICAL

    return AnomalyDetectionUncommited(
        value=deviation,
        time_series_data_id=tsd.id,
        interactive_feedback_mode=False,
    )


def _get_last_interactive_feedback_mode_turned_on(sensor_id: int) -> bool:
    """Get last interactive feedback mode status from the cache.
    If not exist - create a new record base on sensor id.
    """

    try:
        return Cache.get(
            namespace=(CacheNamespace.interactive_mode_turned_on),
            key=sensor_id,
        )
    except NotFoundError:
        Cache.set(
            namespace="anomaly_detection_last_ifb_mode_turned_on",
            key=sensor_id,
            item=False,
        )
        return False


def _process_mode_dispatcher(
    matrix_profile: MatrixProfile,
    tsd: Tsd,
    last_interactive_feedback_mode_turned_on: bool,
    current_interactive_feedback_mode_turned_on: bool,
) -> AnomalyDetectionUncommited:
    """The flow:
    1. Get the last interactive feedback mode from the cache and compare to
        the current in the sensor.configuration.
    2. If last is True and current is False, then the last is changed to False
        and the normal mode is used for processing.
    3. If last is False and current is True, then the last is changed to True,
        the matrix profile is updated/reset,
        the interactive feedback mode is used for processing.
    4. If last is True and current is True, then nothing is happening and
        the interactive feedback mode is used for processing.
    5. If last is False and current is False, then nothing is happening and
        the normal mode is used for processing.
    """

    if (
        last_interactive_feedback_mode_turned_on is True
        and current_interactive_feedback_mode_turned_on is False
    ):
        Cache.set(
            namespace=CacheNamespace.interactive_mode_turned_on,
            key=tsd.sensor.id,
            item=False,
        )
        return normal_mode_processing(matrix_profile, tsd)
    elif (
        last_interactive_feedback_mode_turned_on is False
        and current_interactive_feedback_mode_turned_on is True
    ):
        # Reset the matrix profile if a new interactive
        # feedback processing was started
        matrix_profile.fb_baseline = matrix_profile.fb_baseline_start
        matrix_profile.last_values = matrix_profile.last_values[
            -matrix_profile.window :
        ]
        for value in matrix_profile.last_values:
            matrix_profile.fb_baseline.update(value)

        # Update the cache entry
        Cache.set(
            namespace=CacheNamespace.interactive_mode_turned_on,
            key=tsd.sensor.id,
            item=True,
        )
        return interactive_feedback_mode_processing(matrix_profile, tsd)
    elif (
        last_interactive_feedback_mode_turned_on is False
        and current_interactive_feedback_mode_turned_on is False
    ):
        return normal_mode_processing(matrix_profile, tsd)
    else:
        # True, True option
        return interactive_feedback_mode_processing(matrix_profile, tsd)


def process(tsd: Tsd) -> AnomalyDetectionUncommited:
    """The main anomaly detection processing entrypoint."""

    # Create default matrix profile if not exist
    if not (matrix_profile := MATRIX_PROFILES.get(tsd.sensor.id)):
        logger.success(
            f"A new matrix profile is created for the sensor {tsd.sensor.id}"
        )
        baseline = copy_initial_baseline(level=MatrixProfileLevel.HIGH)
        matrix_profile = MatrixProfile(
            max_dis=np.float64(max(baseline.P_)),
            baseline=baseline,
            fb_max_dis=np.float64(max(baseline.P_)),
            fb_baseline=baseline,
            fb_baseline_start=baseline,
        )
        MATRIX_PROFILES[tsd.sensor.id] = matrix_profile

    last_interactive_feedback_mode_turned_on: bool = (
        _get_last_interactive_feedback_mode_turned_on(tsd.sensor.id)
    )
    current_interactive_feedback_mode_turned_on: bool = (
        tsd.sensor.configuration.interactive_feedback_mode
    )

    try:
        return _process_mode_dispatcher(
            matrix_profile,
            tsd,
            last_interactive_feedback_mode_turned_on,
            current_interactive_feedback_mode_turned_on,
        )
    except AnomalyDetectionMatrixProfileError as error:
        logger.info(str(error))
        return AnomalyDetectionUncommited(
            value=AnomalyDeviation.UNDEFINED,
            time_series_data_id=tsd.id,
            interactive_feedback_mode=False,
        )
