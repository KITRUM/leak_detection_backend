from pathlib import Path

import numpy as np
from pydantic import Field

from src.infrastructure.database import TemplatesTable
from src.infrastructure.models import InternalModel

__all__ = ("TemplateUncommited", "Template")


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
