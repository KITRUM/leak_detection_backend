"""
This module encaplsulates the information about the Time series data that
is fetched from sensors.

On the other hand the external API establishment is also provided here.
"""

from src.domain.tsd.models import *  # noqa: F401, F403
from src.domain.tsd.repository import *  # noqa: F401, F403
from src.domain.tsd import services
