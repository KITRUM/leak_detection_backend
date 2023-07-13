"""
The main purpose of this module is establishing the fake
data source with mocked CSV files.
"""
import asyncio
import csv
from pathlib import Path
from typing import AsyncGenerator

from src.config import settings
from src.domain.sensors import Sensor

__all__ = ("read_from_csv_file",)


async def read_from_csv_file(
    sensor: Sensor,
) -> AsyncGenerator[list[str] | None, None]:
    """
    This function fakes the API call.
    If we do not have the response - the None is returned.
    """

    # Build the file path base on the sensor.tag
    filename: Path = settings.mock_dir / f"tsd/{sensor.name}.csv"

    with open(filename) as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row

        for row in reader:
            # HACK: Simulate the long request from the external source
            await asyncio.sleep(settings.tsd_fetch_periodicity)
            yield row

        # Simulate the case when we do not have the response
        # from the OMNIA API. Or the sensor is not available
        while True:
            await asyncio.sleep(settings.tsd_fetch_periodicity)
            yield None
