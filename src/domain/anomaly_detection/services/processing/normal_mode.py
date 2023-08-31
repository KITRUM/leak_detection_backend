from src.domain.tsd import Tsd

from ...models import (
    AnomalyDetectionUncommited,
    AnomalyDeviation,
    MatrixProfile,
)


def _update_matrix_profile(matrix_profile: MatrixProfile, tsd: Tsd) -> None:
    """Update the matrix profile with the new data."""

    # WARNING: Works only for the normal mode

    if matrix_profile.counter >= (matrix_profile.window * 2):
        # Reset the matrix profile baseline and last values
        matrix_profile.counter = matrix_profile.window

        matrix_profile.baseline = (
            tsd.sensor.configuration.anomaly_detection_initial_baseline
        )
        matrix_profile.last_values = matrix_profile.last_values[
            -matrix_profile.window :
        ]
        for value in matrix_profile.last_values:
            matrix_profile.baseline.update(value)

    matrix_profile.baseline.update(tsd.ppmv)
    matrix_profile.counter += 1
    matrix_profile.last_values.append(tsd.ppmv)


def process(
    matrix_profile: MatrixProfile, tsd: Tsd
) -> AnomalyDetectionUncommited:
    """The regular/normal mode for the anomaly detection process."""

    _update_matrix_profile(matrix_profile, tsd)

    # The processinr is skipped if not enough items in the matrix profile
    if matrix_profile.initial_values_full_capacity is False:
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
