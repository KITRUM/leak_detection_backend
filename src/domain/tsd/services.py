import numpy as np

from src.config import settings
from src.domain.tsd.models import Tsd, TsdFlat, TsdRaw, TsdUncommited
from src.domain.tsd.repository import TsdRepository
from src.infrastructure.database import transaction


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
async def get_last_tsd_set(sensor_id: int, id_: int) -> list[TsdFlat]:
    return [
        tsd
        async for tsd in TsdRepository().fitler_last_by_sensor(
            sensor_id=sensor_id,
            id_=id_,
            limit=settings.anomaly_detection.window_size,
        )
    ]
