import numpy as np
from sqlalchemy import delete

from src.config import settings
from src.infrastructure.database import TimeSeriesDataTable, transaction

from .models import Tsd, TsdInDb, TsdRaw, TsdUncommited
from .repository import TsdRepository


@transaction
async def save_tsd(tsd_raw: TsdRaw, sensor_id: int) -> Tsd:
    repository = TsdRepository()
    tsd: TsdInDb = await repository.create(
        TsdUncommited(
            ppmv=np.float64(tsd_raw.ppmv),
            timestamp=tsd_raw.timestamp,
            sensor_id=sensor_id,
        )
    )
    return await repository.get(tsd.id)


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await TsdRepository().execute(delete(TimeSeriesDataTable))


@transaction
async def get_by_id(id_: int) -> Tsd:
    return await TsdRepository().get(id_=id_)


@transaction
async def get_historical_data(sensor_id: int) -> list[TsdInDb]:
    """Get the historical data."""

    return [tsd async for tsd in TsdRepository().by_sensor(sensor_id)]


@transaction
async def get_last_tsd_set(sensor_id: int, id_: int) -> list[TsdInDb]:
    return [
        tsd
        async for tsd in TsdRepository().fitler_last_by_sensor(
            sensor_id=sensor_id,
            id_=id_,
            limit=settings.anomaly_detection.window_size,
        )
    ]
