import math
from copy import deepcopy
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy import stats
from stumpy import aampi

from src.config import settings

from ...models import AnomalyDeviation, MatrixProfile, SeedBaseline

__all__ = ("select_best_baseline",)


WINDOW_SIZE: int = settings.anomaly_detection.window_size


async def select_best_baseline(
    seed_baselines: list[SeedBaseline],
    cleaned_concentrations: NDArray[np.float64],
) -> SeedBaseline | None:
    """Take all seed baselines and compute the cleaned concentration data
    in order to find the baseline with the less number of errors.
    """

    # Represents the number of error of the selected seed baseline
    # that is processing by the baseline selection feature.
    seed_baselines_errors: dict[Path, int] = {}

    # The result temporary object
    _best_baseline: SeedBaseline | None = None

    ERROR = math.inf  # just a big number
    # Get the list of deviations for each seed baseline base on
    # cleaned concentrations set.

    # Go through all seed baselines and select the best option or None
    for seed_baseline in seed_baselines:
        deviations: list[AnomalyDeviation] = process(
            seed_baseline=seed_baseline,
            concentrations=cleaned_concentrations,
        )

        # NOTE: If there is at least one CRITICAL / WARNING deviation was
        #       faced on cleaned data processing,
        #       this seed baseline should be skipped
        filtered_deviations: set[AnomalyDeviation] = set(deviations)
        if (
            AnomalyDeviation.WARNING in filtered_deviations
            or AnomalyDeviation.CRITICAL in filtered_deviations
        ):
            continue

        # Log the current error
        errors_statistic: int = _get_baseline_errors_statistic(
            cleaned_concentrations=cleaned_concentrations,
            seed_baseline=seed_baseline,
        )
        seed_baselines_errors[seed_baseline.filename] = errors_statistic

        # Get the baseline with the smallest error:
        if errors_statistic < ERROR:
            ERROR = errors_statistic
            _best_baseline = seed_baseline

    return _best_baseline


def process(
    seed_baseline: SeedBaseline, concentrations: NDArray[np.float64]
) -> list[AnomalyDeviation]:
    """The entrypint for processing the baseline selection.
    the seed baseline is a baseline which we gonna test for the selection.
    concentrations are values for all the time.
    """

    matrix_profile = MatrixProfile(
        max_dis=np.float64(max(seed_baseline.baseline.P_)),
        baseline=seed_baseline.baseline,
        fb_max_dis=np.float64(max(seed_baseline.baseline.P_)),
        fb_baseline=seed_baseline.baseline,
        fb_baseline_start=seed_baseline.baseline,
    )

    return [
        _process(
            initial_baseline=seed_baseline.baseline,
            matrix_profile=matrix_profile,
            concentration=concentration,
        )
        for concentration in concentrations
    ]


def _process(
    matrix_profile: MatrixProfile,
    concentration: np.float64,
    initial_baseline: aampi,
) -> AnomalyDeviation:
    """This function is quite the same as a normal mode processing,
    but this one is not checking for the existance of enough TSD items
    and also it does not care about data saving to the database. It just
    returns the deviation for future baselines comparison.
    """

    _update_matrix_profile(
        initial_baseline=initial_baseline,
        matrix_profile=matrix_profile,
        concentration=concentration,
    )

    dis = matrix_profile.baseline.P_[-1:]
    dis_lvl = dis / matrix_profile.max_dis * 100

    if dis_lvl < matrix_profile.warning:
        return AnomalyDeviation.OK
    elif dis_lvl >= matrix_profile.warning and dis_lvl < matrix_profile.alert:
        return AnomalyDeviation.WARNING

    return AnomalyDeviation.CRITICAL


def _update_matrix_profile(
    initial_baseline: aampi,
    matrix_profile: MatrixProfile,
    concentration: np.float64,
):
    """Update the matrix profile with the new data."""

    if matrix_profile.counter >= (matrix_profile.window * 2):
        # Reset the matrix profile baseline and last values
        matrix_profile.counter = matrix_profile.window

        # NOTE: The different line from the normal mode processing function
        matrix_profile.baseline = deepcopy(initial_baseline)

        matrix_profile.last_values = matrix_profile.last_values[
            -matrix_profile.window :
        ]
        for value in matrix_profile.last_values:
            matrix_profile.baseline.update(value)

    matrix_profile.baseline.update(concentration)
    matrix_profile.counter += 1
    matrix_profile.last_values.append(concentration)


def _get_baseline_errors_statistic(
    cleaned_concentrations: NDArray, seed_baseline: SeedBaseline
) -> int:
    """The main goal is to compare statistics of the collected
    and cleaned data with baselines and choose the most similar.
    """

    temp_error = 0

    # get statistics of the cleaned data
    d1 = stats.describe(cleaned_concentrations)
    describe1 = [d1[2], d1[3]]
    describe2 = seed_baseline.stats

    # Getting the metric to compare
    for i, j in zip(describe1, describe2):
        temp_error = temp_error + (j - i) ** 2

    return round(temp_error**0.5)
