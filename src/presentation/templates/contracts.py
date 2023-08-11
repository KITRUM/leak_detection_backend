from pathlib import Path

import numpy as np
from pydantic import Field

from src.config import settings
from src.domain.templates import TemplateUncommited
from src.infrastructure.models import PublicModel


class GeometryInformationPublic(PublicModel):
    """The public representation of the geometry information."""

    fore: float
    aft: float
    port: float
    starboard: float


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
    z_roof: float | None = None

    # Semi-closed parameters
    porosity: GeometryInformationPublic | None = Field(default_factory=None)
    wall_area: GeometryInformationPublic | None = Field(default_factory=None)
    inclination: GeometryInformationPublic | None = Field(default_factory=None)

    internal_volume: float | None = None

    # Required if internal_volume is not defined
    length: float | None = None
    width: float | None = None

    def build_template_uncommited(
        self, platform_id: int
    ) -> TemplateUncommited:
        """Build TemplateUncommited internal instance."""

        currents_path = (
            str(self.currents_path)
            if self.currents_path
            else str(settings.seed_dir / "currents.csv")
        )
        waves_path = (
            str(self.waves_path)
            if self.waves_path
            else str(settings.seed_dir / "waves.csv")
        )
        simulated_leaks_path = (
            str(self.simulated_leaks_path)
            if self.simulated_leaks_path
            else str(settings.seed_dir / "simulated_leaks.csv")
        )

        payload = self.dict() | {
            "currents_path": currents_path,
            "waves_path": waves_path,
            "simulated_leaks_path": simulated_leaks_path,
            "platform_id": platform_id,
            "angle_from_north": np.float64(self.angle_from_north),
            "height": np.float64(self.height) if self.height else None,
            "internal_volume": np.float64(self.internal_volume)
            if self.internal_volume
            else None,
            "length": np.float64(self.length) if self.length else None,
            "width": np.float64(self.width) if self.width else None,
        }

        return TemplateUncommited(**payload)


class TemplateUpdateRequestBody(PublicModel):
    currents_path: Path | None = Field(
        description="The file with currents baseline."
    )
    waves_path: Path | None = Field(
        description="The file with waves baseline.", default=None
    )
    simulated_leaks_path: Path | None = Field(
        description="The file with currents baseline.", default=None
    )

    name: str | None = Field(
        description="The name of the tempalte", default=None
    )
    angle_from_north: float | None = None
    height: float | None = None
    z_roof: float | None = None

    # Semi-closed parameters
    porosity: GeometryInformationPublic | None = Field(default_factory=None)
    wall_area: GeometryInformationPublic | None = Field(default_factory=None)
    inclination: GeometryInformationPublic | None = Field(default_factory=None)

    internal_volume: float | None = None

    # Required if internal_volume is not defined
    length: float | None = None
    width: float | None = None


class TemplatePublic(PublicModel):
    """The public template data model.

    P.S. primitives are used due to the FastAPI limitation.
    """

    id: int

    currents_path: Path
    waves_path: Path
    simulated_leaks_path: Path

    angle_from_north: float
    height: float | None = None
    z_roof: float | None = None

    # Semi-closed parameters
    porosity: GeometryInformationPublic | None = None
    wall_area: GeometryInformationPublic | None = None
    inclination: GeometryInformationPublic | None = None

    internal_volume: np.float64 | None = None

    # Required if internal_volume is not defined
    length: np.float64 | None = None
    width: np.float64 | None = None

    platform_id: int
