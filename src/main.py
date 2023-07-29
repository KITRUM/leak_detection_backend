from fastapi import FastAPI
from loguru import logger

from src.application import anomaly_detection, estimation, simulation, tsd
from src.config import settings
from src.domain.anomaly_detection import services as anomaly_detection_services
from src.domain.estimation import services as estimation_services
from src.domain.simulation import services as simulation_services
from src.domain.tsd import services as tsd_services
from src.infrastructure import application
from src.presentation.anomaly_detection import (
    router as anomaly_detection_router,
)
from src.presentation.estimation import router as estimation_summary_set_router
from src.presentation.sensors import router as sensors_router
from src.presentation.templates import router as templates_router
from src.presentation.tsd import router as tsd_router

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
    shutdown_tasks.append(anomaly_detection_services.delete_all)
    shutdown_tasks.append(tsd_services.delete_all)
    shutdown_tasks.append(simulation_services.delete_all)
    shutdown_tasks.append(estimation_services.delete_all)


# Adjust the application
# -------------------------------
app: FastAPI = application.create(
    debug=settings.debug,
    routers=(
        templates_router,
        sensors_router,
        tsd_router,
        anomaly_detection_router,
        estimation_summary_set_router,
    ),
    startup_tasks=[
        tsd.process_for_existed_sensors,
        anomaly_detection.process,
        simulation.process,
        estimation.process,
    ],
    shutdown_tasks=shutdown_tasks,
)
