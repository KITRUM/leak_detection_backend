from pathlib import Path

import numpy as np
from pydantic import Field

from src.config import settings
from src.infrastructure.database import TemplatesTable
from src.infrastructure.models import InternalModel, PublicModel

__all__ = (
    "TemplateCreateRequestBody",
    "TemplateUncommited",
    "Template",
    "TemplatePublic",
)


class GeometryInformationPublic(InternalModel):
    """The public representation of the geometry information."""

    fore: float
    aft: float
    port: float
    starboard: float


class GeometryInformation(InternalModel):
    fore: np.float32
    aft: np.float32
    port: np.float32
    starboard: np.float32

    @classmethod
    def from_db_field(cls, field: dict | None) -> "GeometryInformation | None":
        return (
            cls(
                fore=np.float32(field["fore"]),
                aft=np.float32(field["aft"]),
                port=np.float32(field["port"]),
                starboard=np.float32(field["starboard"]),
            )
            if field
            else None
        )


class TemplateCreateRequestBody(PublicModel):
    """This data model corresponds to the
    http request body for templates creation.
    """

    currents_path: Path | None = Field(
        description="The file with currents baseline."
    )
    waves_path: Path | None = Field(
        description="The file with waves baseline.", default=None
    )
    simulated_leaks_path: Path | None = Field(
        description="The file with currents baseline.", default=None
    )

    name: str = Field(description="The name of the tempalte")
    angle_from_north: float
    height: float | None = None

    # Semi-closed parameters
    porosity: GeometryInformationPublic | None = Field(default_factory=None)
    wall_area: GeometryInformationPublic | None = Field(default_factory=None)
    inclination: GeometryInformationPublic | None = Field(default_factory=None)

    internal_volume: float | None = None

    # Required if internal_volume is not defined
    length: float | None = None
    width: float | None = None


class TemplateUncommited(InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    currents_path: str
    waves_path: str
    simulated_leaks_path: str

    name: str
    angle_from_north: np.float32
    height: np.float32 | None = None

    # Semi-closed parameters
    porosity: dict | None = Field(default_factory=dict)
    wall_area: dict | None = Field(default_factory=dict)
    inclination: dict | None = Field(default_factory=dict)

    internal_volume: np.float32 | None = None

    # Required if internal_volume is not defined
    length: np.float32 | None = None
    width: np.float32 | None = None

    platform_id: int

    @classmethod
    def from_request(cls, platform_id: int, body: TemplateCreateRequestBody):
        """Build the create schema from the public request data."""

        currents_path = (
            str(body.currents_path)
            if body.currents_path
            else str(settings.seed_dir / "currents.csv")
        )
        waves_path = (
            str(body.waves_path)
            if body.waves_path
            else str(settings.seed_dir / "waves.csv")
        )
        simulated_leaks_path = (
            str(body.simulated_leaks_path)
            if body.simulated_leaks_path
            else str(settings.seed_dir / "simulated_leaks.csv")
        )

        payload = body.dict() | {
            "currents_path": currents_path,
            "waves_path": waves_path,
            "simulated_leaks_path": simulated_leaks_path,
            "platform_id": platform_id,
            "angle_from_north": np.float32(body.angle_from_north),
            "height": np.float32(body.height) if body.height else None,
            "internal_volume": np.float32(body.internal_volume)
            if body.internal_volume
            else None,
            "length": np.float32(body.length) if body.length else None,
            "width": np.float32(body.width) if body.width else None,
        }

        return cls(**payload)


# TODO: This class should be refactored by using pydantic.validator
class Template(TemplateUncommited):
    """The internal template representation."""

    id: int

    currents_path: Path
    waves_path: Path
    simulated_leaks_path: Path

    # Semi-closed parameters
    porosity: GeometryInformation | None = None
    wall_area: GeometryInformation | None = None
    inclination: GeometryInformation | None = None

    @classmethod
    def from_orm(cls, schema: TemplatesTable) -> "Template":
        """Convert ORM schema representation into the internal model."""

        return cls(
            id=schema.id,
            currents_path=Path(schema.currents_path),
            waves_path=Path(schema.waves_path),
            simulated_leaks_path=Path(schema.simulated_leaks_path),
            name=schema.name,
            angle_from_north=np.float32(schema.angle_from_north),
            porosity=GeometryInformation.from_db_field(schema.porosity),
            wall_area=GeometryInformation.from_db_field(schema.wall_area),
            inclination=GeometryInformation.from_db_field(schema.inclination),
            internal_volume=np.float32(schema.internal_volume)
            if schema.internal_volume
            else None,
            length=np.float32(schema.length) if schema.length else None,
            width=np.float32(schema.width) if schema.width else None,
            platform_id=schema.platform_id,
        )


class TemplatePublic(Template, PublicModel):
    """The public template data model.

    P.S. primitives are used due to the FastAPI limitation.
    """

    angle_from_north: float
    height: float | None = None
    internal_volume: float | None = None
    length: float | None = None
    width: float | None = None

    # Semi-closed parameters
    porosity: GeometryInformationPublic | None = None
    wall_area: GeometryInformationPublic | None = None
    inclination: GeometryInformationPublic | None = None
