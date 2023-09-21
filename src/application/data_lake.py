"""
This module includes the producer/consumer implementation for
the project's data lake.

It is not placed in the infrastructure layer,
since it depends on internal data models.

⚠️ Probably this module should be placed between application and domain layers.
Or it should be placed in the infrastructure layer which is more preferable.
"""

import asyncio
from collections import defaultdict, deque
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from typing import AsyncGenerator, Deque, Generic, TypeVar

from src.config import settings
from src.domain.anomaly_detection import AnomalyDetection
from src.domain.events import sensors, system
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


# NOTE: The data lake is implemented in order to reduce the database usage
#       and to provide the data for the websocket connections.
#       Probably it should be replaced with the external service like cache...


@dataclass
class DataLake:
    """This class represents the data lake
    that immitates producer/consumer behaviour.

    P.S. The regular python deque interface is preferable.
    """

    # Storage for reducing the database usage. Uses for background processing
    time_series_data: LakeItem[Tsd]
    # Storage for reducing the database usage. Uses by websocket connection
    time_series_data_by_sensor: dict[int, LakeItem[Tsd]]

    # Uses for background processing by simulation processing
    anomaly_detections_for_simulation: LakeItem[AnomalyDetection]
    # Uses by websocket connection
    anomaly_detections_by_sensor: dict[int, LakeItem[AnomalyDetection]]

    # Events [sensors]
    events_by_sensor: dict[int, LakeItem[sensors.Event]]

    # Events [system]
    events_system: LakeItem[system.Event]


data_lake = DataLake(
    time_series_data=LakeItem[Tsd](),
    time_series_data_by_sensor=defaultdict(partial(LakeItem[Tsd])),
    # Anomaly detection
    anomaly_detections_for_simulation=LakeItem[AnomalyDetection](limit=10),
    anomaly_detections_by_sensor=defaultdict(
        partial(LakeItem[AnomalyDetection])
    ),
    # Events [sensors]
    events_by_sensor=defaultdict(partial(LakeItem[sensors.Event], limit=1)),
    # Events [system]
    events_system=LakeItem[system.Event](limit=20),
)
