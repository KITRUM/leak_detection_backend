"""
This module defines operations with baselines.
All operations
"""
from datetime import datetime

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from stumpy import core, stump

from src.config import settings
from src.domain.sensors.models import Sensor
from src.domain.tsd import TsdFlat
from src.domain.tsd import services as tsd_services
from src.infrastructure.errors import UnprocessableError
from src.infrastructure.errors.base import NotFoundError

WINDOW_SIZE = settings.anomaly_detection.window_size

__all__ = ("clean_concentrations",)


async def clean_concentrations(
    sensor: Sensor,
    last_baseline_selection_timestamp: datetime | None,
) -> NDArray[np.float64]:
    """After TSD items are selected from the database
    it should be cleaned from anomalies before the selection is done.

    The cleaned concentrations set is used for
    the best baseline selection & baseline update features
    """

    try:
        tsd_set: list[
            TsdFlat
        ] = await tsd_services.get_last_set_from_timestamp(
            sensor_id=sensor.id, timestamp=last_baseline_selection_timestamp
        )
    except NotFoundError:
        message = (
            "The baseline selection processing is possible only in case "
            f"time series data exists in the database. Sensor id: {sensor.id}"
        )
        logger.debug(message)

        raise UnprocessableError(message=message)

    # Convert into NDArray[np.float64]
    tsd_items: NDArray[np.float64] = np.array([tsd.ppmv for tsd in tsd_set])

    if (tsd_set_len := len(tsd_items)) < WINDOW_SIZE:
        raise UnprocessableError(
            message=(
                f"The amount of time TSD items ({tsd_set_len}) "
                f"is less then window size ({WINDOW_SIZE})"
            )
        )

    # TODO: Refactor the code below

    # TODO: Define the better k value base on the number of days for consuming
    discords = _get_discords(tsd_items, k=15, normalize=False, finite=False)
    max_accept = _give_acceptable_dist(
        tsd_set=np.array(discords[0]), cut=2000, m=5
    )

    # Cleaning entrypoint
    delete = []

    for i in discords[1]:
        if i[1] > max_accept:
            delete.append(i[0])
        else:
            break

    delete.sort()
    add = []
    start = 0
    delete.append(len(tsd_items))

    # create the
    for i in delete:
        a = i - WINDOW_SIZE
        if a < start:
            a = start
        add.append((start, a))
        if i + WINDOW_SIZE * 2 < len(tsd_items):
            start = i + WINDOW_SIZE * 2
        else:
            start = len(tsd_items)
    result = np.array([])

    for i in add:
        a = i[0]
        b = i[1]
        result = np.concatenate((result, tsd_items[a:b]))

    # TODO: add smoothing here

    return result


def _get_discords(
    tsd_set: NDArray[np.float64],
    k: int = 1,
    normalize: bool = False,
    finite: bool = False,
    exclusion_zone: int = settings.anomaly_detection.window_size // 2,
) -> tuple[list[int], NDArray[np.float64]]:
    """This function cleans the concentration data
    which comes from the database.

    k: int -- amount of discords to find
    """
    unusual: list = []

    mp = stump(
        tsd_set,
        settings.anomaly_detection.window_size,
        normalize=normalize,
    )

    P = mp[:, 0].astype(np.float64)

    if finite:
        P[~np.isfinite(P)] = np.NINF

    discords_idx = np.full(k, -1, dtype=np.int64)
    discords_dist = np.full(k, np.NINF, dtype=np.float64)

    # TODO: Investigate if we do need this unused variable
    # discords_nn_idx = np.full(k, -1, dtype=np.int64)

    for i in range(k):
        if np.all(P == np.NINF):
            break

        mp_discord_idx = np.argmax(P)

        discords_idx[i] = mp_discord_idx
        discords_dist[i] = P[mp_discord_idx]

        try:
            unusual.append(int(P[mp_discord_idx]))
        except OverflowError:
            # NOTE: the int(-inf) raises the error,
            #       then all items with NINF are skipped
            continue

        core.apply_exclusion_zone(
            P,
            discords_idx[i],
            exclusion_zone,
            val=np.NINF,
        )

    out = np.empty((k, 2), dtype=object)

    out[:, 0] = discords_idx
    out[:, 1] = discords_dist

    return unusual, out


def _give_acceptable_dist(tsd_set: NDArray[np.float64], cut, m):
    def reject_outliers(data, m):
        d = np.abs(data - np.median(data))
        mdev = np.median(d)
        s = d / (mdev if mdev else 1.0)

        return data[s < m]

    filter_array = tsd_set < cut
    new_array = tsd_set[filter_array]
    # the data without big outliers
    without_out = reject_outliers(new_array, m)

    # NOTE: There we can get the without_out == []
    #       which raises the error on max()
    return np.max(without_out)
