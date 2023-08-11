from functools import lru_cache
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from src.infrastructure.database import TemplatesTable
from src.infrastructure.models import InternalModel

__all__ = ("TemplateUncommited", "Template")


class GeometryInformation(InternalModel):
    fore: np.float64
    aft: np.float64
    port: np.float64
    starboard: np.float64

    @classmethod
    def from_db_field(cls, field: dict | None) -> "GeometryInformation | None":
        return (
            cls(
                fore=np.float64(field["fore"]),
                aft=np.float64(field["aft"]),
                port=np.float64(field["port"]),
                starboard=np.float64(field["starboard"]),
            )
            if field
            else None
        )

    @property
    @lru_cache(maxsize=1)
    def as_array(self) -> NDArray[np.float64]:
        return np.array([])


class _TemplateBase(InternalModel):
    """The shared template payload."""

    name: str

    angle_from_north: np.float64
    height: np.float64 | None = None
    z_roof: np.float64 | None = None

    internal_volume: np.float64 | None = None

    # Required if internal_volume is not defined
    length: np.float64 | None = None
    width: np.float64 | None = None

    platform_id: int


class TemplateUncommited(_TemplateBase):
    """This schema should be used for passing it
    to the repository operation.
    """

    currents_path: str
    waves_path: str
    simulated_leaks_path: str

    # Semi-closed parameters
    porosity: dict | None = Field(default_factory=dict)
    wall_area: dict | None = Field(default_factory=dict)
    inclination: dict | None = Field(default_factory=dict)


class TemplatePartialUpdateSchema(InternalModel):
    currents_path: str | None = None
    waves_path: str | None = None
    simulated_leaks_path: str | None = None

    name: str | None = None
    angle_from_north: np.float64 | None = None
    height: np.float64 | None = None
    z_roof: np.float64 | None = None

    # Semi-closed parameters
    porosity: dict | None = Field(default=None)
    wall_area: dict | None = Field(default=None)
    inclination: dict | None = Field(default=None)

    internal_volume: np.float64 | None = None

    # Required if internal_volume is not defined
    length: np.float64 | None = None
    width: np.float64 | None = None


# TODO: This class should be refactored by using pydantic.validator
class Template(_TemplateBase):
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
            angle_from_north=np.float64(schema.angle_from_north),
            z_roof=np.float64(schema.z_roof) if schema.z_roof else None,
            porosity=GeometryInformation.from_db_field(schema.porosity),
            wall_area=GeometryInformation.from_db_field(schema.wall_area),
            inclination=GeometryInformation.from_db_field(schema.inclination),
            internal_volume=np.float64(schema.internal_volume)
            if schema.internal_volume
            else None,
            length=np.float64(schema.length) if schema.length else None,
            width=np.float64(schema.width) if schema.width else None,
            platform_id=schema.platform_id,
        )
