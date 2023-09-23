from datetime import timedelta
from pathlib import Path

import numpy as np
from pydantic import BaseConfig, BaseModel, BaseSettings

from src.infrastructure.models import InternalModel


# API Settings
class APIUrlsSettings(BaseModel):
    """Configure public urls."""

    docs: str = "/docs"
    redoc: str = "/redoc"


class PublicApiSettings(BaseModel):
    """Configure public API settings."""

    name: str = "Franatech"
    urls: APIUrlsSettings = APIUrlsSettings()


# Database Settings
class DatabaseSettings(BaseModel):
    name: str = "db.sqlite3"

    @property
    def url(self) -> str:
        return f"sqlite+aiosqlite:///./{self.name}"


# Logging Settings
class LoggingSettings(BaseModel):
    """Configure the logging engine."""

    # The time field can be formatted using more human-friendly tokens.
    # These constitute a subset of the one used by the Pendulum library
    # https://pendulum.eustace.io/docs/#tokens
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | {message}"

    # The .log filename
    file: str = "franatech"

    # The .log file Rotation
    rotation: str = "10MB"

    # The type of compression
    compression: str = "zip"


# Admin Settings
class AdminSettings(BaseModel):
    """Configure the admin panel."""

    title: str = "Leakage detection | by Franatech team"
    base_url: str = "/admin"
    templates_dir: str = "templates/admin"
    logo_url: str = "https://preview.tabler.io/static/logo-white.svg"
    debug: bool = False


# Sensors Settings
class SensorsAnomalyDetectionSettings(BaseModel):
    """This model aggregates anomaly detection
    settings for all sensors.
    """

    # This config determines how often the best baseline selection
    # is happening. The interval is a range between the last time series
    # data consumed and the first one which has to be taken for the process
    baseline_best_selection_interval: timedelta = timedelta(days=15)

    # This config determines how often the sensor's initial baseline
    # update is happening. The interval defines how often this process runs.
    baseline_augmentation_interval: timedelta = timedelta(days=30)


class SensorsSettings(BaseModel):
    anomaly_detection = (
        SensorsAnomalyDetectionSettings
    ) = SensorsAnomalyDetectionSettings()


# Anomaly Detection Settings
class AnomalyDetectionSettings(BaseModel):
    # Defines the extension of the file with the matrix profile data.
    mpstream_file_extension: str = ".mpstream"

    # Determines how many points are skipped before searching the next discord.
    # 🔗 https://stumpy.readthedocs.io/en/latest/Tutorial_STUMPY_Basics.html
    # Find-Potential-Anomalies-(Discords)-using-STUMP
    exclusion_zone: int = 72

    # The discrete of the data frame which determines how many points
    # are used for the anomaly detection prediction
    window_size: int = 144

    # The discrete value which is used as a `limit` for detecting the anomaly
    warning: int = 100
    alert: int = 200

    # This config determines if we should save the interactive feedback
    # results after toggling this feature off.
    # ref: domain/anomaly_detection/services.py:
    #       _save_interactive_feedback_resutls()
    interactive_feedback_save_max_limit: int = 1000


# Simulation Settings
class SimulationParameters(InternalModel):
    seawater_temperature: np.float64 = np.float64(6.2)
    depth: np.float64 = np.float64(70)
    detection_limit: np.float64 = np.float64(5.0e-7)
    current_period: np.float64 = np.float64(2)
    a: np.float64 = np.float64(5.5)
    p: np.float64 = np.float64(-0.4)
    q: np.float64 = np.float64(0.34)
    cd: np.float64 = np.float64(0.001)
    alpha: np.float64 = np.float64(0.32)
    gamma: np.float64 = np.float64(1.224)
    kappa: np.float64 = np.float64(0.41)
    uref: np.float64 = np.float64(0.30)
    tref: int = 600


class SimulationOptions(BaseModel):
    run_open_template: bool = True
    report_ppmv: bool = True
    current_u_v_components: bool = True
    wave_current_interaction: bool = True


class SimulationSettings(BaseModel):
    options: SimulationOptions = SimulationOptions()
    parameters: SimulationParameters = SimulationParameters()
    turn_on: bool = False


# Settings are powered by pydantic
# https://pydantic-docs.helpmanual.io/usage/settings/
class Settings(BaseSettings):
    debug: bool = True

    # Project file system
    root_dir: Path
    seed_dir: Path
    src_dir: Path
    # Contains export data like detection rates, etc...
    export_dir: Path

    # Contains any kind of source data
    mock_dir: Path

    # Infrastructure settings
    database: DatabaseSettings = DatabaseSettings()

    # Application configuration
    public_api: PublicApiSettings = PublicApiSettings()
    logging: LoggingSettings = LoggingSettings()
    admin: AdminSettings = AdminSettings()

    sensors: SensorsSettings = SensorsSettings()
    anomaly_detection: AnomalyDetectionSettings = AnomalyDetectionSettings()
    simulation: SimulationSettings = SimulationSettings()

    tsd_fetch_periodicity: float = 0.05
    data_lake_consuming_periodicity: float = 0.05

    class Config(BaseConfig):
        env_nested_delimiter: str = "__"
        env_file: str = ".env"


# ======================================
# Define the root path
# ======================================
ROOT_PATH = Path(__file__).parent.parent

# ======================================
# Load settings
# ======================================
settings = Settings(
    # NOTE: We would like to hard-code the root and applications directories
    #       to avoid overriding via environment variables
    root_dir=ROOT_PATH,
    seed_dir=ROOT_PATH / "seed",
    src_dir=ROOT_PATH / "src",
    mock_dir=ROOT_PATH / "mock",
    export_dir=ROOT_PATH / "export",
)
