"""
This modules collects the time series data processing services.
The general purpose: fetch the data from the external source and parse it
using the specific platform parser.
"""

import asyncio

from loguru import logger

from src.application.data_lake import data_lake
from src.application.tsd import mock
from src.config import settings
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.tsd import Tsd, TsdRaw, services

__all__ = ("process", "process_for_existed_sensors")


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
        tsd: Tsd = await services.save_tsd(tsd_raw, sensor.id)

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


async def process_for_existed_sensors():
    """This function is used as a background task reference."""

    logger.success("Background time series data fetching is started")

    async for sensor in SensorsRepository().all():
        asyncio.create_task(process(sensor))