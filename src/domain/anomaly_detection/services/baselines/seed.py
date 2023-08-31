"""
This module includes all operations with seed files
which are required by the anomaly detection component.
"""

import pickle
from os import listdir
from pathlib import Path

from stumpy import aampi

from src.config import settings
from src.infrastructure.errors import NotFoundError

from ...constants import SEED_BASELINES_STATS_BY_FILENAME
from ...models import SeedBaseline


def for_select_best() -> list[SeedBaseline]:
    """Returns the list of stumpy objects
    which are used for the `selection` feature.

    The storage of baselines for the selection are stored
    in a seed/baselines/selection/.
    """

    baselines_root: Path = settings.seed_dir / "baselines/selection"

    results: list[SeedBaseline] = []

    for filename in listdir(baselines_root):
        filename_absolute = baselines_root / filename

        # NOTE: files which consist of not serializable
        #       object by pickle should be skipped
        if (
            filename_absolute.suffix
            is not settings.anomaly_detection.mpstream_file_extension
        ):
            continue

        with open(filename_absolute, mode="rb") as file:
            results.append(
                SeedBaseline(
                    filename=filename_absolute,
                    baseline=pickle.load(file),
                    stats=SEED_BASELINES_STATS_BY_FILENAME[filename],
                )
            )

    return results


def by_level(level: str) -> aampi:
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
