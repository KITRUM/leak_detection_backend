import pickle
from os import listdir
from typing import Generator

from stumpy import aampi

from src.config import settings
from src.domain.sensors.models import Sensor
from src.infrastructure.errors import NotFoundError


def get_from_seed_for_selection() -> Generator[aampi, None, None]:
    """Returns the list of stumpy objects
    which are used for the `selection` feature.

    The storage of baselines for the selection are stored
    in a seed/baselines/selection/.
    """

    for filename in listdir(settings.seed_dir / "baselines/selection"):
        with open(filename, mode="rb") as file:
            yield pickle.load(file)


def get_from_seed(level: str) -> aampi:
    """Returns the baseline from seed files on file system.
    This baseline is using as an initial baseline on sensor creation.
    """

    match level:
        case "low":
            return pickle.load(
                open(f"{settings.seed_dir}/baselines/low.mpstream", "rb")
            )
        case "high":
            return pickle.load(
                open(f"{settings.seed_dir}/baselines/high.mpstream", "rb")
            )
        case _:
            raise NotFoundError(
                message=f"Can not find the initial baseline for {level=}"
            )


def get_initial_by_sensor(sensor: Sensor) -> aampi:
    """Converts the database representation of the initial baseline
    which is in bytes into the specific stumpy object.
    """

    baseline_flat: bytes = (
        sensor.configuration.initial_anomaly_detection_baseline
    )

    return pickle.loads(baseline_flat)
