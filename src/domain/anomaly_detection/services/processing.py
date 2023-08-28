import numpy as np
from loguru import logger
from stumpy import aampi

from src.config import settings
from src.domain.sensors.models import Sensor
from src.domain.tsd import Tsd
from src.infrastructure.cache import Cache
from src.infrastructure.errors import NotFoundError

from ..constants import (
    ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE,
    CacheNamespace,
)
from ..models import (
    AnomalyDetectionUncommited,
    AnomalyDeviation,
    MatrixProfile,
)
from .baselines import get_initial_baseline_by_sensor

__all__ = ("process",)


# TODO: Should be moved to the infrastructure later.
MATRIX_PROFILES: dict[int, MatrixProfile] = {}


def _update_matrix_profile(matrix_profile: MatrixProfile, tsd: Tsd) -> None:
    """Update the matrix profile with the new data."""

    # WARNING: Works only for the normal mode

    if matrix_profile.counter >= (matrix_profile.window * 2):
        # Reset the matrix profile baseline and last values
        matrix_profile.counter = matrix_profile.window

        matrix_profile.baseline = get_initial_baseline_by_sensor(tsd.sensor)
        matrix_profile.last_values = matrix_profile.last_values[
            -matrix_profile.window :
        ]
        for value in matrix_profile.last_values:
            matrix_profile.baseline.update(value)

    matrix_profile.baseline.update(tsd.ppmv)
    matrix_profile.counter += 1
    matrix_profile.last_values.append(tsd.ppmv)


def interactive_feedback_mode_processing(
    matrix_profile: MatrixProfile, tsd: Tsd
) -> AnomalyDetectionUncommited:
    """The interactive feedback mode processing implementation.
    It is used in case the sensor.configuration.interactive_feedback_mode
    is turned on.
    """

    print(f"Interactive feedback mode processing for {tsd.id}")

    # Update the matrix profile baseline
    if matrix_profile.counter >= (matrix_profile.window * 2):
        # Reset the matrix profile baseline and last values
        matrix_profile.counter = matrix_profile.window

        # TODO: Get the initial baseline from the sensor instead
        # ====================================================================
        matrix_profile.fb_baseline = get_initial_baseline_by_sensor(tsd.sensor)
        matrix_profile.last_values = matrix_profile.last_values[
            -matrix_profile.window :
        ]
        for value in matrix_profile.last_values:
            matrix_profile.fb_baseline.update(value)

    matrix_profile.fb_baseline.update(tsd.ppmv)
    matrix_profile.counter += 1
    matrix_profile.last_values.append(tsd.ppmv)

    # The processing is skipped if not enough items in the matrix profile
    if matrix_profile.initial_values_full_capacity is False:
        logger.info(
            ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE.format(
                matrix_profile_counter=matrix_profile.counter
            )
        )
        return AnomalyDetectionUncommited(
            value=AnomalyDeviation.UNDEFINED,
            time_series_data_id=tsd.id,
            interactive_feedback_mode=True,
        )

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

    _update_matrix_profile(matrix_profile, tsd)

    # The processing is skipped if not enough items in the matrix profile
    if matrix_profile.initial_values_full_capacity is False:
        logger.info(
            ANOMALY_DETECTION_MATRIX_PROFILE_ERROR_MESSAGE.format(
                matrix_profile_counter=matrix_profile.counter
            )
        )
        return AnomalyDetectionUncommited(
            value=AnomalyDeviation.UNDEFINED,
            time_series_data_id=tsd.id,
            interactive_feedback_mode=False,
        )

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


def _get_or_create_last_interactive_feedback_mode_turned_on(
    sensor_id: int,
) -> bool:
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


def _save_interactive_feedback_resutls(
    matrix_profile: MatrixProfile, sensor: Sensor
):
    """After user toggle off the interactive feedback
    all results have to be saved.
    """

    # TODO: Get the initial baseline from the sensor instead
    # ====================================================================
    matrix_profile.baseline = get_initial_baseline_by_sensor(sensor)

    if matrix_profile.fb_temp and (
        max(matrix_profile.fb_temp)
        >= settings.anomaly_detection.interactive_feedback_save_max_limit
    ):
        return

    matrix_profile.fb_historical += matrix_profile.fb_temp

    for value in matrix_profile.fb_temp:
        matrix_profile.fb_baseline_start.update(value)

    # Prepare the baseline to the next start
    matrix_profile.fb_temp = []
    matrix_profile.fb_max_dis = max(matrix_profile.fb_baseline_start._P)


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

    # NOTE: Toggle OFF the interactive feedback
    if (
        last_interactive_feedback_mode_turned_on is True
        and current_interactive_feedback_mode_turned_on is False
    ):
        Cache.set(
            namespace=CacheNamespace.interactive_mode_turned_on,
            key=tsd.sensor.id,
            item=False,
        )
        _save_interactive_feedback_resutls(matrix_profile, tsd.sensor)
        return normal_mode_processing(matrix_profile, tsd)
    # NOTE: Toggle ON the interactive feedback
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
    # NOTE: Toggle OFF is not changed
    elif (
        last_interactive_feedback_mode_turned_on is False
        and current_interactive_feedback_mode_turned_on is False
    ):
        return normal_mode_processing(matrix_profile, tsd)
    # NOTE: Toggle ON is not changed
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
        baseline: aampi = get_initial_baseline_by_sensor(tsd.sensor)

        matrix_profile = MatrixProfile(
            max_dis=np.float64(max(baseline.P_)),
            baseline=baseline,
            fb_max_dis=np.float64(max(baseline.P_)),
            fb_baseline=baseline,
            fb_baseline_start=baseline,
        )
        MATRIX_PROFILES[tsd.sensor.id] = matrix_profile

    # For the first `window size` number of items we receive it is needed
    # skip processing for populating the first matrix profile
    if (
        matrix_profile.initial_values_full_capacity is False
        and matrix_profile.counter >= settings.anomaly_detection.window_size
    ):
        matrix_profile.initial_values_full_capacity = True

    last_interactive_feedback_mode_turned_on: bool = (
        _get_or_create_last_interactive_feedback_mode_turned_on(tsd.sensor.id)
    )
    current_interactive_feedback_mode_turned_on: bool = (
        tsd.sensor.configuration.interactive_feedback_mode
    )

    return _process_mode_dispatcher(
        matrix_profile,
        tsd,
        last_interactive_feedback_mode_turned_on,
        current_interactive_feedback_mode_turned_on,
    )
