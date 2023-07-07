import numpy as np
from sqlalchemy import delete

from src.application.database import transaction
from src.domain.tsd.models import Tsd, TsdInDb, TsdRaw, TsdUncommited
from src.domain.tsd.repository import TsdRepository
from src.infrastructure.database import TimeSeriesDataTable


@transaction
async def save_tsd(tsd_raw: TsdRaw, sensor_id: int) -> Tsd:
    repository = TsdRepository()
    tsd: TsdInDb = await repository.create(
        TsdUncommited(
            ppmv=np.float32(tsd_raw.ppmv),
            timestamp=tsd_raw.timestamp,
            sensor_id=sensor_id,
        )
    )
    return await repository.get(tsd.id)


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await TsdRepository().execute(delete(TimeSeriesDataTable))
