from typing import Callable

import numpy as np
from loguru import logger
from stumpy import aampi

from src.config import settings
from src.domain.tsd import Tsd
from src.infrastructure.cache import Cache

from ...constants import CacheNamespace
from ...models import AnomalyDetectionUncommited, MatrixProfile
from .modes import interactive_feedback as interactive_feedback_mode
from .modes import normal as normal_mode

__all__ = ("dispatch",)


# TODO: Should be moved to the infrastructure later.
MATRIX_PROFILES: dict[int, MatrixProfile] = {}

_ProcessingCallback = Callable[
    [MatrixProfile, Tsd], AnomalyDetectionUncommited
]


def dispatch(tsd: Tsd) -> AnomalyDetectionUncommited:
    """The main anomaly detection processing entrypoint."""

    # Create default matrix profile if not exist
    if not (matrix_profile := MATRIX_PROFILES.get(tsd.sensor.id)):
        baseline: aampi = (
            tsd.sensor.configuration.anomaly_detection_initial_baseline
        )

        max_dis: np.float64 = np.float64(max(baseline.P_))

        matrix_profile = MatrixProfile(
            max_dis=max_dis,
            baseline=baseline,
            fb_max_dis=max_dis,
            fb_baseline=baseline,
            fb_baseline_start=baseline,
        )
        MATRIX_PROFILES[tsd.sensor.id] = matrix_profile

        logger.success(
            f"A new matrix profile is created for the sensor {tsd.sensor.id}"
        )

    # For the first `window size` number of items we receive it is needed
    # skip processing for populating the first matrix profile
    if (
        matrix_profile.initial_values_full_capacity is False
        and matrix_profile.counter >= settings.anomaly_detection.window_size
    ):
        matrix_profile.initial_values_full_capacity = True

    last_interactive_feedback_mode_turned_on: bool = (
        interactive_feedback_mode.get_or_create_from_cache(tsd.sensor.id)
    )
    current_interactive_feedback_mode_turned_on: bool = (
        tsd.sensor.configuration.interactive_feedback_mode
    )

    callback: _ProcessingCallback = _process_mode_dispatcher(
        matrix_profile,
        tsd,
        last_interactive_feedback_mode_turned_on,
        current_interactive_feedback_mode_turned_on,
    )

    return callback(matrix_profile, tsd)


def _process_mode_dispatcher(
    matrix_profile: MatrixProfile,
    tsd: Tsd,
    last_interactive_feedback_mode_turned_on: bool,
    current_interactive_feedback_mode_turned_on: bool,
) -> _ProcessingCallback:
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
        interactive_feedback_mode.save_results(matrix_profile, tsd.sensor)

        return normal_mode.process

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

        return interactive_feedback_mode.process

    # NOTE: Toggle OFF is not changed
    elif (
        last_interactive_feedback_mode_turned_on is False
        and current_interactive_feedback_mode_turned_on is False
    ):
        return normal_mode.process

    # NOTE: Toggle ON is not changed
    else:
        # True, True option
        return interactive_feedback_mode.process
