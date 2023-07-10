from pathlib import Path

from pydantic import BaseConfig, BaseModel, BaseSettings


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
    rotation: str = "1MB"

    # The type of compression
    compression: str = "zip"


class AnomalyDetectionSettings(BaseModel):
    window_size: int = 144
    warning: int = 100
    alert: int = 200


class SimulationOptions(BaseModel):
    run_open_template: bool = True
    report_ppmv: bool = True
    current_u_v_components: bool = True
    wave_current_interaction: bool = True


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

    anomaly_detection: AnomalyDetectionSettings = AnomalyDetectionSettings()

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
