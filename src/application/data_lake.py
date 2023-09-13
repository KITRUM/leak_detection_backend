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
from src.domain.estimation import EstimationSummary
from src.domain.events import sensors, templates
from src.domain.simulation import SimulationDetectionRateFlat
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

    # Storage for reducing the database usage. Uses for background processing
    time_series_data: LakeItem[Tsd]
    # Storage for reducing the database usage. Uses by websocket connection
    time_series_data_by_sensor: dict[int, LakeItem[Tsd]]

    # Uses for background processing by simulation processing
    anomaly_detections_for_simulation: LakeItem[AnomalyDetection]
    # Uses by websocket connection
    anomaly_detections_by_sensor: dict[int, LakeItem[AnomalyDetection]]

    # Storage for reducing the database usage. Uses for background processing
    simulation_detection_rates: LakeItem[list[SimulationDetectionRateFlat]]

    # Storage for reducing the database usage. Uses by websocket connection
    estimation_summary_set_by_sensor: dict[int, LakeItem[EstimationSummary]]

    # Events [sensors]
    events_by_sensor: dict[int, LakeItem[sensors.Event]]

    # Events [templates]
    events_by_template: dict[int, LakeItem[templates.Event]]


data_lake = DataLake(
    time_series_data=LakeItem[Tsd](),
    time_series_data_by_sensor=defaultdict(partial(LakeItem[Tsd])),
    # Anomaly detection
    anomaly_detections_for_simulation=LakeItem[AnomalyDetection](limit=10),
    anomaly_detections_by_sensor=defaultdict(
        partial(LakeItem[AnomalyDetection])
    ),
    # Simulation
    simulation_detection_rates=LakeItem[list[SimulationDetectionRateFlat]](
        limit=10
    ),
    # Estimation
    estimation_summary_set_by_sensor=defaultdict(
        partial(LakeItem[EstimationSummary], limit=10)
    ),
    # Events [sensors]
    events_by_sensor=defaultdict(partial(LakeItem[sensors.Event], limit=1)),
    # Events [templates]
    events_by_template=defaultdict(
        partial(LakeItem[templates.Event], limit=1)
    ),
)
