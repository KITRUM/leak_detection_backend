from datetime import datetime

from pydantic import Field

from src.infrastructure.models import PublicModel

from .constants import (
    SENSOR_CONFIGURATION_INTERACTIVE_FEEDBACK_MODE_DESCRIPTION,
    SENSOR_CONFIGURATION_PINNED_DESCRIPTION,
)

__all__ = ("SensorConfigurationUpdateRequestBody", "SensorConfigurationPublic")


class SensorConfigurationUpdateRequestBody(PublicModel):
    """Allows None in order to be used with PATCH update."""

    pinned: str | None = Field(
        default=None, description=SENSOR_CONFIGURATION_PINNED_DESCRIPTION
    )

    interactive_feedback_mode: bool | None = Field(
        default=None,
        description=(
            SENSOR_CONFIGURATION_INTERACTIVE_FEEDBACK_MODE_DESCRIPTION
        ),
    )
    last_baseline_selection_timestamp: datetime | None = None
    last_baseline_update_timestamp: datetime | None = None


class SensorConfigurationPublic(PublicModel):
    """This model represents the public sensor's configuration."""

    pinned: bool | None = Field(
        default=None, description=SENSOR_CONFIGURATION_PINNED_DESCRIPTION
    )

    interactive_feedback_mode: bool = Field(
        description=SENSOR_CONFIGURATION_INTERACTIVE_FEEDBACK_MODE_DESCRIPTION
    )
