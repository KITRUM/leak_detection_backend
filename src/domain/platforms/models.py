from src.infrastructure.models import InternalModel

__all__ = ("PlatformInfo",)


class PlatformInfo(InternalModel):
    """
    This internal model represent the Platform in the database.
    It is used in domain.platforms.constants
    """

    id: int
    name: str
