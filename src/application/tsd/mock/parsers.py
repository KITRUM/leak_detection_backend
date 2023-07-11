from datetime import datetime
from typing import Callable

from src.domain.platforms import Platform
from src.domain.tsd import TsdRaw
from src.infrastructure.errors.base import NotFoundError

__all__ = ("PlatformParserCallback", "get_parser")


RAW_TSD_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
RAW_TSD_DATE_FORMAT_MILISECONDS = "%Y-%m-%d %H:%M:%S.%f"

PlatformParserCallback = Callable[[list[str]], TsdRaw]


def trestakk_parser(raw_data: list[str]) -> TsdRaw:
    """The trestakk parser mock time series data parser.

    The example of mocked data (from the mock/19XT2116.csv file):
    -   -------------------         ------------------
        Time                        Values
    -   -------------------         ------------------
    0   2020-04-25 03:39:28.812     38.75863265991211
    1   2020-04-25 03:59:28.812     40.84138870239258
    """

    return TsdRaw(
        timestamp=datetime.strptime(
            raw_data[1], RAW_TSD_DATE_FORMAT_MILISECONDS
        ),
        ppmv=float(raw_data[2]),
    )


def snorre_parser(raw_data: list[str]) -> TsdRaw:
    """The snorre parser mock time series data parser.

    The example of mocked data (from the mock/snorre.csv file):
    -----   -------------------  ----    ----------
            timestamp            5472    time_diff
    -----   -------------------  ----    ----------
    590695  2021-04-05 14:06:57  92.2
    590706  2021-04-05 14:12:42  89.2    0 days 00:05:45
    """

    return TsdRaw(
        timestamp=datetime.strptime(raw_data[1], RAW_TSD_DATE_FORMAT),
        ppmv=float(raw_data[2]),
    )


def get_parser(platform_id: int) -> PlatformParserCallback:
    """Get the parser by platform id."""

    match Platform.get_by_id(platform_id):
        case Platform.TRESTAKK:
            return trestakk_parser
        case Platform.SNORRE:
            return snorre_parser
        case _:
            raise NotFoundError(
                message=f"Unknown platform parser: {platform_id}"
            )
