"""
System events component is about "system" events, like:
    - sensor is down
    - sensor is up
    - best baseline has been selected
    - baseline has beed updated

System events shold appear on the operator's screen based on the severity.
"""

from .models import *  # noqa: F401, F403
from .repository import *  # noqa: F401, F403
