from datetime import datetime

import numpy as np

from src.config import settings
from src.infrastructure.database import transaction

from .models import Tsd, TsdFlat, TsdRaw, TsdUncommited
from .repository import TsdRepository


@transaction
async def save_tsd(tsd_raw: TsdRaw, sensor_id: int) -> Tsd:
    repository = TsdRepository()
    tsd: TsdFlat = await repository.create(
        TsdUncommited(
            ppmv=np.float64(tsd_raw.ppmv),
            timestamp=tsd_raw.timestamp,
            sensor_id=sensor_id,
        )
    )
    return await repository.get(tsd.id)


@transaction
async def get_by_id(id_: int) -> Tsd:
    return await TsdRepository().get(id_=id_)


@transaction
async def get_historical_data(sensor_id: int) -> list[TsdFlat]:
    """Get the historical data."""

    return [tsd async for tsd in TsdRepository().by_sensor(sensor_id)]


@transaction
async def get_last_window_size_set(
    sensor_id: int, last_id: int
) -> list[TsdFlat]:
    """Returns last `window size` number of TSD instances."""

    return [
        tsd
        async for tsd in TsdRepository().by_sensor(
            sensor_id=sensor_id,
            last_id=last_id,
            limit=settings.anomaly_detection.window_size,
        )
    ]


@transaction
async def get_last_set_from_timestamp(
    sensor_id: int, timestamp: datetime | None = None
) -> list[TsdFlat]:
    if not timestamp:
        return [
            instance async for instance in TsdRepository().by_sensor(sensor_id)
        ]

    return [
        instance
        async for instance in TsdRepository().by_sensor(
            sensor_id=sensor_id, timestamp_from=timestamp
        )
    ]
