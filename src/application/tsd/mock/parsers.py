from typing import Callable

from dateutil.parser import parse as datetime_parser

from src.domain.fields import Field
from src.domain.tsd import TsdRaw
from src.infrastructure.errors.base import NotFoundError

__all__ = ("FieldParserCallback", "get_parser")


FieldParserCallback = Callable[[list[str]], TsdRaw]


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
        timestamp=datetime_parser(raw_data[1]), ppmv=float(raw_data[2])
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
        timestamp=datetime_parser(raw_data[1]), ppmv=float(raw_data[2])
    )


def get_parser(field_id: int) -> FieldParserCallback:
    """Get the parser by field id."""

    match Field.get_by_id(field_id):
        case Field.TRESTAKK:
            return trestakk_parser
        case Field.SNORRE:
            return snorre_parser
        case _:
            raise NotFoundError(message=f"Unknown field parser: {field_id}")
