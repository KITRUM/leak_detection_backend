from functools import partial
from typing import Callable

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


# Define startup tasks
# -------------------------------
# NOTE: tasks are running in a sequence
startup_tasks: list[Callable] = []

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
            coro=application.anomaly_detection.process(),
        ),
        partial(
            tasks.run,
            namespace="simulation",
            key="processing",
            coro=application.simulation.process(),
        ),
        partial(
            tasks.run,
            namespace="estimation",
            key="processing",
            coro=application.estimation.process(),
        ),
        partial(
            tasks.run,
            namespace="events",
            key="process",
            coro=application.events.process(),
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
            namespace="baseline_selection",
            key="processing",
            callback=application.baselines.selection.process,
        ),
    ),
)
