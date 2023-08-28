from csv import DictReader
from functools import lru_cache
from pathlib import Path

from src.infrastructure.database import transaction

from .models import (
    Leakage,
    SimulationDetectionRateFlat,
    SimulationDetectionRateUncommited,
)
from .repository import SimulationDetectionRatesRepository


@transaction
async def save_simulation_detection_rate(
    schema: SimulationDetectionRateUncommited,
) -> SimulationDetectionRateFlat:
    instance: SimulationDetectionRateFlat = (
        await SimulationDetectionRatesRepository().create(schema)
    )

    return instance


@lru_cache(maxsize=1)
def load_leakages_dataset(path: Path) -> list[Leakage]:
    """Read raw currents data from .csv file
    and transform it into the internal data models.
    """

    with open(path) as file:
        reader = DictReader(file)
        return [Leakage.from_raw(row) for row in reader]
