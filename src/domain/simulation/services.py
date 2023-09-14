from csv import DictReader
from functools import lru_cache
from pathlib import Path

from .models import Leakage


@lru_cache(maxsize=1)
def load_leakages_dataset(path: Path) -> list[Leakage]:
    """Read raw currents data from .csv file
    and transform it into the internal data models.
    """

    with open(path) as file:
        reader = DictReader(file)
        return [Leakage.from_raw(row) for row in reader]
