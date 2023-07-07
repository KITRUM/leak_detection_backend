from datetime import datetime
from typing import TypeVar

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

__all__ = (
    "Base",
    "ConcreteTable",
    "TemplatesTable",
    "SensorsTable",
    "TimeSeriesDataTable",
    "AnomalyDetectionsTable",
    "EventsTable",
)

meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class _Base:
    """Base class for all database models."""

    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=_Base, metadata=meta)

ConcreteTable = TypeVar("ConcreteTable", bound=Base)  # type: ignore


class TemplatesTable(Base):
    __tablename__ = "templates"

    currents_path: str = Column(String, nullable=False)  # type: ignore
    waves_path: str = Column(String, nullable=False)  # type: ignore
    simulated_leaks_path: str = Column(String, nullable=False)  # type: ignore

    name: str = Column(String, nullable=False)  # type: ignore
    angle_from_north: float = Column(Float, nullable=False)  # type: ignore
    height: float = Column(Float, nullable=True, default=None)  # type: ignore

    # Semi-closed parameters
    porosity: dict | None = Column(JSON, nullable=True, default=None)  # type: ignore
    wall_area: dict | None = Column(JSON, nullable=True, default=None)  # type: ignore
    inclination: dict | None = Column(JSON, nullable=True, default=None)  # type: ignore
    internal_volume: float | None = Column(Float, nullable=True, default=None)  # type: ignore

    # below parameters only required if internal_volume is not defined
    length: float = Column(Float, nullable=True, default=None)  # type: ignore
    width: float = Column(Float, nullable=True, default=None)  # type: ignore

    platform_id: int = Column(Integer, nullable=False)  # type: ignore

    sensors = relationship("SensorsTable", back_populates="template")
    events = relationship("EventsTable", back_populates="template")


class SensorsTable(Base):
    __tablename__ = "sensors"

    name: str = Column(String, nullable=False, unique=True)  # type: ignore
    x: float = Column(Float, nullable=False)  # type: ignore
    y: float = Column(Float, nullable=False)  # type: ignore
    z: float = Column(Float, nullable=False)  # type: ignore

    template_id: int = Column(
        ForeignKey(TemplatesTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    template = relationship(
        "TemplatesTable", uselist=False, back_populates="sensors"
    )
    time_series_data = relationship(
        "TimeSeriesDataTable", back_populates="sensor"
    )


class TimeSeriesDataTable(Base):
    __tablename__ = "time_series_data"

    ppmv: float = Column(Float, nullable=False)  # type: ignore[var-annotated]
    timestamp: datetime = Column(
        DateTime, nullable=False
    )  # type: ignore[var-annotated]

    sensor_id: int = Column(
        ForeignKey(SensorsTable.id, ondelete="RESTRICT"),
    )  # type: ignore[var-annotated]

    sensor = relationship(
        "SensorsTable", uselist=False, back_populates="time_series_data"
    )

    anomaly_detections = relationship(
        "AnomalyDetectionsTable",
        uselist=False,
        back_populates="time_series_data",
    )


class AnomalyDetectionsTable(Base):
    __tablename__ = "anomaly_detections"

    value: str = Column(String, nullable=False)  # type: ignore[var-annotated]

    time_series_data_id: int = Column(
        ForeignKey(TimeSeriesDataTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    time_series_data = relationship(
        "TimeSeriesDataTable",
        uselist=False,
        back_populates="anomaly_detections",
    )


class EventsTable(Base):
    __tablename__ = "events"

    type_: str = Column(String, nullable=False)  # type: ignore
    message: str = Column(String, nullable=False)  # type: ignore

    template_id: int = Column(
        ForeignKey(TemplatesTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    template = relationship(
        "TemplatesTable", uselist=False, back_populates="events"
    )
