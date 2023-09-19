from datetime import datetime
from typing import TypeVar

from sqlalchemy import (
    BLOB,
    JSON,
    Boolean,
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
    "SensorsConfigurationsTable",
    "SensorsTable",
    "TimeSeriesDataTable",
    "AnomalyDetectionsTable",
    "SimulationDetectionRatesTable",
    "EstimationsSummariesTable",
    "SensorsEventsTable",
    "SystemEventsTable",
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

    currents_path: str = Column(
        String, nullable=False
    )  # type: ignore[var-annotated]
    waves_path: str = Column(
        String, nullable=False
    )  # type: ignore[var-annotated]
    simulated_leaks_path: str = Column(
        String, nullable=False
    )  # type: ignore[var-annotated]

    name: str = Column(String, nullable=False)  # type: ignore[var-annotated]
    angle_from_north: float = Column(
        Float, nullable=False
    )  # type: ignore[var-annotated]
    height: float = Column(
        Float, nullable=True, default=None
    )  # type: ignore[var-annotated]
    z_roof: float = Column(
        Float, nullable=True, default=None
    )  # type: ignore[var-annotated]

    # Semi-closed parameters
    porosity: dict | None = Column(
        JSON, nullable=True, default=None
    )  # type: ignore[var-annotated]
    wall_area: dict | None = Column(
        JSON, nullable=True, default=None
    )  # type: ignore[var-annotated]
    inclination: dict | None = Column(
        JSON, nullable=True, default=None
    )  # type: ignore[var-annotated]
    internal_volume: float | None = Column(
        Float,
        nullable=True,
        default=None,
    )  # type: ignore[var-annotated]

    # below parameters only required if internal_volume is not defined
    length: float = Column(Float, nullable=True, default=None)  # type: ignore
    width: float = Column(Float, nullable=True, default=None)  # type: ignore

    field_id: int = Column(Integer, nullable=False)  # type: ignore

    sensors = relationship("SensorsTable", back_populates="template")

    def __str__(self) -> str:
        return str(self.name)


class SensorsConfigurationsTable(Base):
    __tablename__ = "sensors_configurations"

    pinned: bool = Column(
        Boolean, nullable=False, default=False
    )  # type: ignore[var-annotated]

    interactive_feedback_mode: bool = Column(
        Boolean, nullable=False, default=False
    )  # type: ignore[var-annotated]

    anomaly_detection_initial_baseline_raw: bytes = Column(
        BLOB,
        nullable=False,
    )  # type: ignore[var-annotated]

    # ℹ️ The last TSD instance that was using for the baseline selection
    last_baseline_selection_timestamp: datetime | None = Column(
        DateTime, nullable=True, default=None
    )  # type: ignore[var-annotated]

    # ℹ️ The last TSD instance that was using for the baseline update
    last_baseline_update_timestamp: datetime | None = Column(
        DateTime, nullable=True, default=None
    )  # type: ignore[var-annotated]

    sensor = relationship(
        "SensorsTable", uselist=False, back_populates="configuration"
    )

    def __str__(self) -> str:
        return str(self.id)


class SensorsTable(Base):
    __tablename__ = "sensors"

    name: str = Column(
        String, nullable=False, unique=True
    )  # type: ignore[var-annotated]
    x: float = Column(Float, nullable=False)  # type: ignore[var-annotated]
    y: float = Column(Float, nullable=False)  # type: ignore[var-annotated]
    z: float = Column(Float, nullable=False)  # type: ignore[var-annotated]

    configuration_id: int = Column(
        ForeignKey(SensorsConfigurationsTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]
    configuration = relationship(
        "SensorsConfigurationsTable", back_populates="sensor"
    )

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

    def __str__(self) -> str:
        return str(self.name)


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

    def __str__(self) -> str:
        return f"{self.ppmv} | {self.timestamp}"


class AnomalyDetectionsTable(Base):
    __tablename__ = "anomaly_detections"

    value: str = Column(String, nullable=False)  # type: ignore[var-annotated]
    interactive_feedback_mode: bool = Column(
        Boolean,
        nullable=False,
        default=False,
    )  # type: ignore[var-annotated]

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

    def __str__(self) -> str:
        return f"{self.value} | {self.interactive_feedback_mode}"


class SimulationDetectionRatesTable(Base):
    __tablename__ = "simulation_detection_rates"

    leakage: dict = Column(JSON, nullable=False)  # type: ignore[var-annotated]
    concentrations: str = Column(
        String, nullable=False
    )  # type: ignore[var-annotated]
    rate: float = Column(Float, nullable=False)  # type: ignore[var-annotated]

    anomaly_detection_id: int = Column(
        ForeignKey(AnomalyDetectionsTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    anomaly_detection = relationship(
        "AnomalyDetectionsTable",
        uselist=False,
        back_populates="simulation_detection_rates",
    )

    def __str__(self) -> str:
        return str(self.rate)


class EstimationsSummariesTable(Base):
    __tablename__ = "estimations_summaries"

    result: str = Column(String, nullable=False)  # type: ignore[var-annotated]
    confidence: float = Column(
        Float, nullable=False
    )  # type: ignore[var-annotated]
    simulation_detection_rate_ids: str = Column(
        String, nullable=False
    )  # type: ignore[var-annotated]

    sensor_id: int = Column(
        ForeignKey(SensorsTable.id, ondelete="RESTRICT"),
    )  # type: ignore[var-annotated]

    sensor = relationship(
        "SensorsTable", uselist=False, back_populates="estimation_summary_set"
    )

    def __str__(self) -> str:
        return str(self.result)


class SensorsEventsTable(Base):
    __tablename__ = "sensors_events"

    type: str = Column(String, nullable=False)  # type: ignore[var-annotated]

    sensor_id: int = Column(
        ForeignKey(SensorsTable.id),
        nullable=False,
    )  # type: ignore[var-annotated]

    sensor = relationship(
        "SensorsTable", uselist=False, back_populates="events"
    )

    def __str__(self) -> str:
        return str(self.type)


class SystemEventsTable(Base):
    __tablename__ = "system_events"

    type: str = Column(String, nullable=False)  # type: ignore[var-annotated]
    message: str = Column(
        String,
        nullable=False,
    )  # type: ignore[var-annotated]

    def __str__(self) -> str:
        return f"[{self.type}]: {self.message}"
