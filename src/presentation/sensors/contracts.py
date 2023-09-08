from datetime import datetime

from pydantic import Field

from src.infrastructure.models import PublicModel

__all__ = (
    "SensorCreateRequestBody",
    "SensorUpdateRequestBody",
    "SensorPublic",
    "SensorConfigurationPublic",
)

# Sensor constants
SENSOR_CONFIGURATION_DESCRIPTION = "The configuration of the sensor"
SENSOR_NAME_DESCRIPTION = "The name of the sensor"
SENSOR_X_DESCRIPTION = "The x position of the sensor"
SENSOR_Y_DESCRIPTION = "The y position of the sensor"
SENSOR_Z_DESCRIPTION = "The z position of the sensor"


# Sensor Configuration constants
PINNED_DESCRIPTION = (
    "This field determines if the sensor is pinned on the dashboard"
)
INTERACTIVE_FEEDBACK_MODE_DESCRIPTION = (
    "This fied determines if the interactive feedback mode "
    "feature is turned on for that sensor. If the value is `false`, "
    "then, the anomaly detection processing will be ran in normal mode"
)
LAST_BASELINE_SELECTION_TIMESTAMP_DESCRIPTION = (
    "The last TSD instance that was using for the baseline selection"
)

LAST_BASELINE_AUGMENTATION_TIMESTAMP_DESCRIPTION = (
    "The last TSD instance that was using for the baseline augmentation"
)


# ************************************************
# ********** Sensor configuration **********
# ************************************************
class SensorConfigurationPublic(PublicModel):
    """This model represents the public sensor's configuration."""

    pinned: bool | None = Field(default=None, description=PINNED_DESCRIPTION)

    interactive_feedback_mode: bool = Field(
        description=INTERACTIVE_FEEDBACK_MODE_DESCRIPTION
    )
    last_baseline_selection_timestamp: datetime | None = Field(
        default=None,
        description=LAST_BASELINE_SELECTION_TIMESTAMP_DESCRIPTION,
    )
    last_baseline_augmentation_timestamp: datetime | None = Field(
        default=None,
        description=LAST_BASELINE_AUGMENTATION_TIMESTAMP_DESCRIPTION,
    )


# ************************************************
# ********** Sensor **********
# ************************************************
class SensorCreateRequestBody(PublicModel):
    """This data model corresponds to the http request body
    for sensor creation. It does not include the configuration, since
    the configuration creates automatically with defaults.
    """

    name: str = Field(description=SENSOR_NAME_DESCRIPTION)
    x: float = Field(description=SENSOR_X_DESCRIPTION)
    y: float = Field(description=SENSOR_Y_DESCRIPTION)
    z: float = Field(description=SENSOR_Z_DESCRIPTION)


class SensorUpdateRequestBody(PublicModel):
    """This data model corresponds to the http request body
    for sensor partial update.
    """

    name: str | None = Field(description=SENSOR_NAME_DESCRIPTION, default=None)
    x: float | None = Field(description=SENSOR_X_DESCRIPTION, default=None)
    y: float | None = Field(description=SENSOR_Y_DESCRIPTION, default=None)
    z: float | None = Field(description=SENSOR_Z_DESCRIPTION, default=None)


class SensorPublic(SensorCreateRequestBody):
    """The public sensor data model."""

    id: int
    configuration: SensorConfigurationPublic = Field(
        description=SENSOR_CONFIGURATION_DESCRIPTION
    )
