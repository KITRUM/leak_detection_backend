from enum import StrEnum

from pydantic import Field

from src.infrastructure.models import PublicModel


# ************************************************
# ********** Sensors CRUD **********
# ************************************************
class SensorCreateRequestBody(PublicModel):
    """This data model corresponds to the
    http request body for sensor creation.
    """

    name: str = Field(description="The name of the sensor")
    x: float = Field(description="The x position of the sensor")
    y: float = Field(description="The y position of the sensor")
    z: float = Field(description="The z position of the sensor")


class SensorConfigurationPublic(PublicModel):
    interactive_feedback_mode: bool = Field(
        description=(
            "This field reflects if the sensor works "
            "in the interactive feedback mode."
        ),
    )


class SensorPublic(SensorCreateRequestBody):
    """The public sensor data model."""

    id: int
    configuration: SensorConfigurationPublic = Field(
        description="The configuration of the sensor"
    )


# ************************************************
# ********** SensorConfigurations CRUD ***********
# ************************************************
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


class SensorConfigurationPublic(PublicModel):
    """The public CRUD model, which is used for response."""

    interactive_feedback_mode: bool = Field(
        description=(
            "This fied determines if the interactive feedback mode"
            "feature is turned on for that sensor. If the value is `false`,"
            "then, the anomaly detection processing will be ran in normal mode"
        )
    )
