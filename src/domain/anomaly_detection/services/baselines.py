import pickle

from stumpy import aampi

from src.config import settings
from src.domain.sensors.models import Sensor
from src.infrastructure.errors import NotFoundError

__all__ = ("get_initial_baseline_from_seed", "get_initial_baseline_by_sensor")


def get_initial_baseline_from_seed(level: str) -> aampi:
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


def get_initial_baseline_by_sensor(sensor: Sensor) -> aampi:
    """Converts the database representation of the initial baseline
    which is in bytes into the specific stumpy object.
    """

    baseline_flat: bytes = (
        sensor.configuration.initial_anomaly_detection_baseline
    )

    return pickle.loads(baseline_flat)
