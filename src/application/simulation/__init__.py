"""
This package takes over running the simulation.
It dispatches the data flow and logic between next domains:
    - simulation
    - currents
    - waves
"""

from . import crud  # noqa: F401
from . import plume2d  # noqa: F401
from .core import *  # noqa: F401, F403
