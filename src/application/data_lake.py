"""
This module includes the producer/consumer implementation for
the project's data lake.

It is not placed in the infrastructure layer since it depends on internal data models.
"""

import asyncio
from collections import defaultdict, deque
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from typing import AsyncGenerator, Deque, Generic, TypeVar

from src.config import settings
from src.domain.anomaly_detection import AnomalyDetection

# from src.domain.simulation import SimulationResult
from src.domain.tsd import Tsd

T = TypeVar("T")


# TODO: The deque size should be changed to the window size 2 times.
# ------------------------------------------------------------------
class LakeItem(Generic[T]):
    def __init__(
        self, limit: int | None = None, init_clear: bool = True
    ) -> None:
        self._init_clear: bool = init_clear
        self.storage: Deque[T] = deque(maxlen=limit)

    async def consume(self) -> AsyncGenerator[T, None]:
        """This function is created in order not to obuse the database
        on the websockets calls.
        """

        # NOTE: Clearing the storage is needed since first the historical
        #       data is sent via websocket connection. That's why
        #       duplications could exist which has to be handled.
        if self._init_clear is True:
            self.storage.clear()

        while True:
            with suppress(IndexError):
                # Get the first element from the deque
                yield self.storage.popleft()

            await asyncio.sleep(settings.data_lake_consuming_periodicity)


@dataclass
class DataLake:
    """This class represents the data leak
    that immitates producer/consumer behaviour.

    P.S. The regular python deque interface is preferable.
    """

    # Storage for reducing the database usage. Used for background processing
    time_series_data: LakeItem[Tsd]

    # Storage for reducing the database usage. Used by websocket connection
    time_series_data_by_sensor: dict[int, LakeItem[Tsd]]

    # Storage for reducing the database usage. Used for background processing
    anomaly_detections: LakeItem[AnomalyDetection]

    # Storage for reducing the database usage. Used by websocket connection
    anomaly_detections_by_sensor: dict[int, LakeItem[AnomalyDetection]]

    # Storage for reducing the database usage. Used for background processing
    # simulation_results: LakeItem[SimulationDeprecatedResult]


# TODO: Add limits

data_lake = DataLake(
    time_series_data=LakeItem[Tsd](),
    time_series_data_by_sensor=defaultdict(partial(LakeItem[Tsd])),
    anomaly_detections=LakeItem[AnomalyDetection](),
    anomaly_detections_by_sensor=defaultdict(
        partial(LakeItem[AnomalyDetection])
    ),
    # simulation_results=LakeItem[SimulationDeprecatedResult](),
)
