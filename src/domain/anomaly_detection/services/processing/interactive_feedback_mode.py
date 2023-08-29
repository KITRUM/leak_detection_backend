from src.config import settings
from src.domain.sensors.models import Sensor
from src.domain.tsd import Tsd
from src.infrastructure.cache import Cache
from src.infrastructure.errors import NotFoundError

from ...constants import CacheNamespace
from ...models import (
    AnomalyDetectionUncommited,
    AnomalyDeviation,
    MatrixProfile,
)
from .. import baselines


def process(
    matrix_profile: MatrixProfile, tsd: Tsd
) -> AnomalyDetectionUncommited:
    """The interactive feedback mode processing implementation.
    It is used in case the sensor.configuration.interactive_feedback_mode
    is turned on.
    """

    # Update the matrix profile baseline
    if matrix_profile.counter >= (matrix_profile.window * 2):
        # Reset the matrix profile baseline and last values
        matrix_profile.counter = matrix_profile.window
        matrix_profile.fb_baseline = baselines.get_initial_by_sensor(
            tsd.sensor
        )
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


def get_or_create_from_cache(sensor_id: int) -> bool:
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


def save_results(matrix_profile: MatrixProfile, sensor: Sensor):
    """After user toggle off the interactive feedback
    all results have to be saved.
    """

    matrix_profile.baseline = baselines.get_initial_by_sensor(sensor)

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
