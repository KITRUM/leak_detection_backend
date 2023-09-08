from pydantic import Field

from src.infrastructure.models import PublicModel

from .configurations import (
    SensorConfigurationPublic,
    SensorConfigurationUpdateRequestBody,
)
from .constants import (
    SENSOR_CONFIGURATION_DESCRIPTION,
    SENSOR_NAME_DESCRIPTION,
    SENSOR_X_DESCRIPTION,
    SENSOR_Y_DESCRIPTION,
    SENSOR_Z_DESCRIPTION,
)

__all__ = (
    "SensorCreateRequestBody",
    "SensorUpdateRequestBody",
    "SensorPublic",
)


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

    configuration: SensorConfigurationUpdateRequestBody | None = Field(
        description=SENSOR_CONFIGURATION_DESCRIPTION, default=None
    )


class SensorPublic(SensorCreateRequestBody):
    """The public sensor data model."""

    id: int
    configuration: SensorConfigurationPublic = Field(
        description=SENSOR_CONFIGURATION_DESCRIPTION
    )
