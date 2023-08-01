from fastapi import FastAPI
from loguru import logger

from src import application, domain, presentation
from src.config import settings
from src.infrastructure.application import create as application_factory

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
    shutdown_tasks.append(domain.anomaly_detection.services.delete_all)
    shutdown_tasks.append(domain.tsd.services.delete_all)
    shutdown_tasks.append(domain.simulation.services.delete_all)
    shutdown_tasks.append(domain.estimation.services.delete_all)
    shutdown_tasks.append(domain.events.sensors.services.delete_all)
    shutdown_tasks.append(domain.events.templates.services.delete_all)


# Adjust the application
# -------------------------------
app: FastAPI = application_factory(
    debug=settings.debug,
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
