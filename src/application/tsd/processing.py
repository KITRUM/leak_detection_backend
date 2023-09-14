"""
The general purpose: fetch the data from the external source and parse it
using the specific platform parser.

Also, crud operations for the time series data are implemented here.
"""

from functools import partial

import numpy as np

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.tsd import Tsd, TsdFlat, TsdRaw, TsdRepository, TsdUncommited
from src.infrastructure.application import tasks
from src.infrastructure.database import transaction

from ..tsd import mock

__all__ = (
    "process",
    "create_tasks_for_existed_sensors_process",
    "get_historical_data",
    "get_by_id",
    "create",
)


# ************************************************
# ********** CRUD operations **********
# ************************************************
@transaction
async def create(tsd_raw: TsdRaw, sensor_id: int) -> Tsd:
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

    return [tsd async for tsd in TsdRepository().filter(sensor_id)]


# ************************************************
# ********** Processing **********
# ************************************************
async def _mock_process_time_series_data(sensor):
    """The mock implementation of time series data
    pre processing using CSV files.
    """

    parser: mock.PlatformParserCallback = mock.get_parser(
        sensor.template.platform_id
    )

    # Get the raw string from the CSV file and parse is to the internal model
    async for row in mock.read_from_csv_file(sensor):
        if not row:
            continue

        tsd_raw: TsdRaw = parser(row)

        # NOTE: Some files have pick values that we'd like
        #       to avoide for the demo
        if tsd_raw.ppmv > 10000:
            continue

        tsd: Tsd = await create(tsd_raw, sensor.id)

        # Update the data lake for background processing
        data_lake.time_series_data.storage.append(tsd)
        # Update the data lake for websocket connections
        data_lake.time_series_data_by_sensor[tsd.sensor.id].storage.append(tsd)


async def process(sensor: Sensor):
    """The general interface for fetching and parsing the time series data
    that is taken from the external source.

    The production OMNIA API flow is refected by default
    due to Equinore request waiting till September.
    """

    if settings.debug is True:
        await _mock_process_time_series_data(sensor)

    raise NotImplementedError(
        "This feature is not available due to OMNIA API access issues"
    )


async def create_tasks_for_existed_sensors_process():
    """Run a batch of background tasks."""

    async for sensor in SensorsRepository().filter():
        await tasks.run(
            namespace="sensor_tsd_process",
            key=sensor.id,
            coro=partial(process, sensor),
        )
