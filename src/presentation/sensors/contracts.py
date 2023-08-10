from enum import StrEnum

from pydantic import Field

from src.infrastructure.models import PublicModel


class SensorCreateRequestBody(PublicModel):
    """This data model corresponds to the http request body
    for sensor creation. It does not include the configuration, since
    the configuration creates automatically with defaults.
    """

    # TODO: The optional configuration should be added to the request

    name: str = Field(description="The name of the sensor")
    x: float = Field(description="The x position of the sensor")
    y: float = Field(description="The y position of the sensor")
    z: float = Field(description="The z position of the sensor")


class SensorConfigurationUpdateRequestBody(PublicModel):
    """Allows None in order to be used with PATCH update."""

    interactive_feedback_mode: bool | None = Field(
        default=None,
        description=(
            "This fied determines if the interactive feedback mode"
            "feature is turned on for that sensor. If the value is `false`,"
            "then, the anomaly detection processing will be ran in normal mode"
        ),
    )


class SensorUpdateRequestBody(PublicModel):
    name: str | None = Field(
        description="The name of the sensor", default=None
    )
    x: float | None = Field(
        description="The x position of the sensor", default=None
    )
    y: float | None = Field(
        description="The y position of the sensor", default=None
    )
    z: float = Field(description="The z position of the sensor", default=None)

    configuration: SensorConfigurationUpdateRequestBody | None = Field(
        description="The sensor's configuration", default=None
    )


class SensorConfigurationPublic(PublicModel):
    """This model represents the public sensor's configuration."""

    interactive_feedback_mode: bool = Field(
        description=(
            "This fied determines if the interactive feedback mode"
            "feature is turned on for that sensor. If the value is `false`,"
            "then, the anomaly detection processing will be ran in normal mode"
        )
    )


class SensorPublic(SensorCreateRequestBody):
    """The public sensor data model."""

    id: int
    configuration: SensorConfigurationPublic = Field(
        description="The configuration of the sensor"
    )
