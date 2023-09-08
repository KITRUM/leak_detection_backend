from datetime import datetime

from pydantic import Field

from src.infrastructure.models import PublicModel

# Just some fields descriptions constants
_SENSOR_CONFIGURATION_DESCRIPTION = "The configuration of the sensor"
_SENSOR_NAME_DESCRIPTION = "The name of the sensor"
_SENSOR_X_DESCRIPTION = "The x position of the sensor"
_SENSOR_Y_DESCRIPTION = "The y position of the sensor"
_SENSOR_Z_DESCRIPTION = "The z position of the sensor"

_SENSOR_CONFIGURATION_PINNED_DESCRIPTION = (
    "This field determines if the sensor is pinned on the dashboard"
)
_SENSOR_CONFIGURATION_INTERACTIVE_FEEDBACK_MODE_DESCRIPTION = (
    "This fied determines if the interactive feedback mode "
    "feature is turned on for that sensor. If the value is `false`, "
    "then, the anomaly detection processing will be ran in normal mode"
)


class SensorCreateRequestBody(PublicModel):
    """This data model corresponds to the http request body
    for sensor creation. It does not include the configuration, since
    the configuration creates automatically with defaults.
    """

    # TODO: The optional configuration should be added to the request

    name: str = Field(description=_SENSOR_NAME_DESCRIPTION)
    x: float = Field(description=_SENSOR_X_DESCRIPTION)
    y: float = Field(description=_SENSOR_Y_DESCRIPTION)
    z: float = Field(description=_SENSOR_Z_DESCRIPTION)


class SensorConfigurationUpdateRequestBody(PublicModel):
    """Allows None in order to be used with PATCH update."""

    pinned: str | None = Field(
        default=None, description=_SENSOR_CONFIGURATION_PINNED_DESCRIPTION
    )

    interactive_feedback_mode: bool | None = Field(
        default=None,
        description=(
            _SENSOR_CONFIGURATION_INTERACTIVE_FEEDBACK_MODE_DESCRIPTION
        ),
    )
    last_baseline_selection_timestamp: datetime | None = None
    last_baseline_update_timestamp: datetime | None = None


class SensorUpdateRequestBody(PublicModel):
    name: str | None = Field(
        description=_SENSOR_NAME_DESCRIPTION, default=None
    )
    x: float | None = Field(description=_SENSOR_X_DESCRIPTION, default=None)
    y: float | None = Field(description=_SENSOR_Y_DESCRIPTION, default=None)
    z: float | None = Field(description=_SENSOR_Z_DESCRIPTION, default=None)

    configuration: SensorConfigurationUpdateRequestBody | None = Field(
        description=_SENSOR_CONFIGURATION_DESCRIPTION, default=None
    )


class SensorConfigurationPublic(PublicModel):
    """This model represents the public sensor's configuration."""

    pinned: str | None = Field(
        default=None, description=_SENSOR_CONFIGURATION_PINNED_DESCRIPTION
    )

    interactive_feedback_mode: bool = Field(
        description=_SENSOR_CONFIGURATION_INTERACTIVE_FEEDBACK_MODE_DESCRIPTION
    )


class SensorPublic(SensorCreateRequestBody):
    """The public sensor data model."""

    id: int
    configuration: SensorConfigurationPublic = Field(
        description=_SENSOR_CONFIGURATION_DESCRIPTION
    )
