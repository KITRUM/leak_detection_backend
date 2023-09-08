from functools import partial
from typing import Callable, Coroutine

from fastapi import FastAPI
from loguru import logger
from sqladmin import Admin

from src import application, debug, presentation
from src.config import settings
from src.infrastructure.application import (
    factory,
    middlewares,
    processes,
    tasks,
)
from src.infrastructure.database import engine

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
    "\nThe sensor's anomaly detection baseline revision interval: "
    f"{settings.sensors.anomaly_detection.baseline_revision_interval}"
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
            key="select_best_initial_baseline",
            callback=application.sensors.select_best_baseline,
        ),
        partial(
            processes.run,
            namespace="sensors",
            key="initial_baseline_revision",
            callback=application.sensors.initial_baseline_revision,
        ),
    ),
)


# Adjust the admin panel
# -------------------------------
admin = Admin(
    app=app,
    engine=engine,
    title=settings.admin.title,
    base_url=settings.admin.base_url,
    templates_dir=settings.admin.templates_dir,
    logo_url=settings.admin.logo_url,
    debug=settings.admin.debug,
)

admin.add_view(presentation.templates.TemplatesAdminView)
admin.add_view(presentation.sensors.SensorsAdminView)
admin.add_view(presentation.sensors.SensorsConfigurationsAdminView)
admin.add_view(presentation.tsd.TimeSeriesDataAdminView)
admin.add_view(presentation.anomaly_detection.AnomalyDetectionsAdminView)
admin.add_view(presentation.simulation.SimulationDetectionRatesAdminView)
admin.add_view(presentation.estimation.EstimationAdminView)
admin.add_view(presentation.events.templates.TemplateEventsAdminView)
admin.add_view(presentation.events.sensors.SensorEventsAdminView)
