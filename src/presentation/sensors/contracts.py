from pydantic import Field

from src.infrastructure.models import PublicModel


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
