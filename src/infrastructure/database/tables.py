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
    "SimulationDetectionRatesTable",
    "EstimationsSummariesTable",
    "TemplatesEventsTable",
    "SensorsEventsTable",
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
    z_roof: float = Column(Float, nullable=True, default=None)  # type: ignore

    # Semi-closed parameters
    porosity: dict | None = Column(  # type: ignore
        JSON,
        nullable=True,
        default=None,
    )
    wall_area: dict | None = Column(  # type: ignore
        JSON,
        nullable=True,
        default=None,
    )
    inclination: dict | None = Column(  # type: ignore
        JSON,
        nullable=True,
        default=None,
    )
    internal_volume: float | None = Column(  # type: ignore
        Float,
        nullable=True,
        default=None,
    )

    # below parameters only required if internal_volume is not defined
    length: float = Column(Float, nullable=True, default=None)  # type: ignore
    width: float = Column(Float, nullable=True, default=None)  # type: ignore

    platform_id: int = Column(Integer, nullable=False)  # type: ignore

    sensors = relationship("SensorsTable", back_populates="template")
    events = relationship("TemplatesEventsTable", back_populates="template")


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
    estimation_summary_set = relationship(
        "EstimationsSummariesTable", back_populates="sensor"
    )
    events = relationship("SensorsEventsTable", back_populates="sensor")


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

    anomaly_detection = relationship(
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
        back_populates="anomaly_detection",
    )

    simulation_detection_rates = relationship(
        "SimulationDetectionRatesTable",
        uselist=True,
        back_populates="anomaly_detection",
    )


class SimulationDetectionRatesTable(Base):
    __tablename__ = "simulation_detection_rates"

    leakage: dict = Column(JSON, nullable=False)  # type: ignore
    concentrations: str = Column(String, nullable=False)  # type: ignore
    rate: float = Column(Float, nullable=False)  # type: ignore

    anomaly_detection_id: int = Column(
        ForeignKey(AnomalyDetectionsTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    anomaly_detection = relationship(
        "AnomalyDetectionsTable",
        uselist=False,
        back_populates="simulation_detection_rates",
    )


class EstimationsSummariesTable(Base):
    __tablename__ = "estimations_summaries"

    result: str = Column(String, nullable=False)  # type: ignore
    confidence: float = Column(Float, nullable=False)  # type: ignore
    simulation_detection_rate_ids: str = Column(
        String, nullable=False
    )  # type: ignore[var-annotated]

    sensor_id: int = Column(
        ForeignKey(SensorsTable.id, ondelete="RESTRICT"),
    )  # type: ignore[var-annotated]

    sensor = relationship(
        "SensorsTable", uselist=False, back_populates="estimation_summary_set"
    )


class TemplatesEventsTable(Base):
    __tablename__ = "templates_events"

    type: str = Column(String, nullable=False)  # type: ignore

    template_id: int = Column(
        ForeignKey(TemplatesTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    template = relationship(
        "TemplatesTable", uselist=False, back_populates="events"
    )


class SensorsEventsTable(Base):
    __tablename__ = "sensors_events"

    type: str = Column(String, nullable=False)  # type: ignore

    sensor_id: int = Column(
        ForeignKey(SensorsTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    sensor = relationship(
        "SensorsTable", uselist=False, back_populates="events"
    )
