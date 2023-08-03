from fastapi import FastAPI
from loguru import logger

from src import application, domain, presentation
from src.config import settings
from src.infrastructure.application import create as application_factory
from src.infrastructure.application import middlewares

# Adjust the logging
# -------------------------------
logger.add(
    "".join(
        [
            str(settings.root_dir),
            "/logs/",
            settings.logging.file.lower(),
            ".log",
        ]
    ),
    format=settings.logging.format,
    rotation=settings.logging.rotation,
    compression=settings.logging.compression,
    level="INFO",
)


# Define shutdown tasks
# -------------------------------
# NOTE: tasks are running in a sequence
shutdown_tasks = []

if settings.debug is True:
    shutdown_tasks.extend(
        [
            domain.anomaly_detection.services.delete_all,
            domain.tsd.services.delete_all,
            domain.simulation.services.delete_all,
            domain.estimation.services.delete_all,
            domain.events.sensors.services.delete_all,
            domain.events.templates.services.delete_all,
        ]
    )

# Adjust the application
# -------------------------------
app: FastAPI = application_factory(
    debug=settings.debug,
    middlewares=[
        middlewares.cors,
    ],
    routers=(
        presentation.templates.router,
        presentation.sensors.router,
        presentation.tsd.router,
        presentation.anomaly_detection.router,
        presentation.estimation.router,
        presentation.events.sensors.router,
        presentation.events.templates.router,
    ),
    startup_tasks=[
        application.tsd.process_for_existed_sensors,
        application.anomaly_detection.process,
        application.simulation.process,
        application.estimation.process,
        application.events.process,
    ],
    shutdown_tasks=shutdown_tasks,
)
