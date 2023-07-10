"""
This module includes the producer/consumer implementation for
the project's data lake.

It is not placed in the infrastructure layer since it depends
on internal data models.
"""

import asyncio
from collections import defaultdict, deque
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from typing import AsyncGenerator, Deque, Generic, TypeVar

from src.domain.anomaly_detection import AnomalyDetection
from src.domain.tsd import Tsd

T = TypeVar("T")


# TODO: The deque size should be changed to the window size 2 times.
# ------------------------------------------------------------------
class LakeItem(Generic[T]):
    def __init__(self, limit: int | None = None) -> None:
        self.storage: Deque[T] = deque(maxlen=limit)

    async def consume(self) -> AsyncGenerator[T, None]:
        """This function is created in order not to obuse the database
        on the websockets calls.
        """

        # NOTE: Clearing the storage is needed since first the historical
        #       data is sent via websocket connection. That's why
        #       duplications could exist which has to be handled.
        self.storage.clear()

        while True:
            with suppress(IndexError):
                # Get the first element from the deque
                yield self.storage.popleft()

            await asyncio.sleep(0.5)


@dataclass
class DataLake:
    """This class represents the data leak
    that immitates producer/consumer behaviour.

    P.S. The regular python deque interface is preferable.
    """

    time_series_data: LakeItem[Tsd]  # for background processing
    time_series_data_by_sensor: dict[
        int, LakeItem[Tsd]
    ]  # websockets consuming
    anomaly_detections: LakeItem[AnomalyDetection]  # for background processing
    anomaly_detections_by_sensor: dict[
        int, LakeItem[AnomalyDetection]
    ]  # websockets consuming
    matrix_profiles: dict[int, LakeItem[dict]]


data_lake = DataLake(
    time_series_data=LakeItem[Tsd](),
    time_series_data_by_sensor=defaultdict(partial(LakeItem[Tsd], limit=200)),
    anomaly_detections=LakeItem[AnomalyDetection](),
    anomaly_detections_by_sensor=defaultdict(
        partial(LakeItem[AnomalyDetection], limit=200)
    ),
    matrix_profiles=defaultdict(partial(LakeItem[dict], limit=200)),
)
