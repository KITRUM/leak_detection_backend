from functools import partial
from typing import Callable, Coroutine

from fastapi import FastAPI
from loguru import logger

from src import application, debug, presentation
from src.config import settings
from src.infrastructure.application import (
    factory,
    middlewares,
    processes,
    tasks,
)

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

# Output some settings
logger.debug(
    "\n*******************************************************************"
    "\nSETTINGS"
    "\n*******************************************************************"
    "\nThe TSD fetching from the external source periodicity: "
    f"{settings.tsd_fetch_periodicity}"
    "\nThe data lake consuming periodicity: "
    f"{settings.data_lake_consuming_periodicity}"
    "\nThe sensor's anomaly detection baseline best selection interval: "
    f"{settings.sensors.anomaly_detection.baseline_best_selection_interval}"
    "\nThe sensor's anomaly detection baseline udpate interval: "
    f"{settings.sensors.anomaly_detection.baseline_update_interval}"
    "\n*******************************************************************"
)

# Define startup tasks
# -------------------------------
# NOTE: tasks are running in a sequence
startup_tasks: list[Callable[[], Coroutine]] = []

# Extend with dev tasks
if settings.debug is True:
    startup_tasks.extend([debug.reset_the_database])

startup_tasks.extend(
    [
        application.tsd.create_tasks_for_existed_sensors_process,
        partial(
            tasks.run,
            namespace="anomaly_detection",
            key="processing",
            coro=application.anomaly_detection.process,
        ),
        partial(
            tasks.run,
            namespace="simulation",
            key="processing",
            coro=application.simulation.process,
        ),
        partial(
            tasks.run,
            namespace="estimation",
            key="processing",
            coro=application.estimation.process,
        ),
        partial(
            tasks.run,
            namespace="events",
            key="process",
            coro=application.events.process,
        ),
    ]
)

# Adjust the application
# -------------------------------
app: FastAPI = factory.create(
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
    startup_tasks=startup_tasks,
    startup_processes=(
        partial(
            processes.run,
            namespace="sensors",
            key="select_best_baseline",
            callback=application.sensors.select_best_baseline,
        ),
    ),
)
