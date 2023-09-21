"""
The purpose of this module is reflecting the general idea
of the simulation processing that producing the detection rates
"""

import numpy as np
from loguru import logger

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.anomaly_detection.models import AnomalyDetection
from src.domain.currents import Current
from src.domain.currents import services as currents_services
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.simulation import (
    CartesianCoordinates,
    Detection,
    DetectionUncommited,
    Leakage,
    SimulationDetectionsRepository,
)
from src.domain.simulation import services as simulation_services
from src.infrastructure.application import processes
from src.infrastructure.database import transaction
from src.infrastructure.physics import constants

from . import plume2d

__all__ = ("process",)


def get_sensor_transformed_coordinates(
    sensor: Sensor, leak: Leakage, current: Current
) -> CartesianCoordinates:
    """Transforms the (x,y)-coordinates to fit
    into a cartesian coordinate system where:
    - The leak is at the origin in the (x,y)-plane
    - The x-axis points along the direction of the current
    """
    # Rotate the coordinates so that the x-axis points
    # along the direction of the current
    rotate_angle = (
        current.angle_from_north
        - constants.PI / 2
        - sensor.template.angle_from_north
    )
    alpha = np.cos(rotate_angle)
    beta = np.sin(rotate_angle)

    coordinates = CartesianCoordinates(
        x=np.float64(sensor.x * alpha - sensor.y * beta),
        y=np.float64(sensor.x * beta + sensor.y * alpha),
    )

    transformed_leak_x = np.float64(leak.x * alpha - leak.y * beta)
    transformed_leak_y = np.float64(leak.x * beta + leak.y * alpha)

    # Shift the coordinates so that the origin is at the leak
    coordinates.x -= transformed_leak_x
    coordinates.y -= transformed_leak_y

    return coordinates


async def process():
    """Consume fetched anomaly detection from data lake and run the simulation.
    The result is produced back to data lake and saved
    to the database for making the history available.
    WARNING: files are loaded only once for the whole processing

    WARNING: Wave and currents datasets should have the same amount of values,
             since it is required by the processing algorithm.
    """

    # NOTE: Skip if settings are set to False
    if not settings.simulation.turn_on:
        return

    if settings.debug is False:
        raise NotImplementedError(
            "Currently the simulation is not working with real data"
        )

    if settings.simulation.options.run_open_template is False:
        raise NotImplementedError(
            "Closed template simulation is not implemented yet"
        )

    leakages_dataset: list[
        Leakage
    ] = simulation_services.load_leakages_dataset(
        settings.mock_dir / "simulated_leakages.csv"
    )
    currents_dataset: list[Current] = currents_services.load_currents_dataset(
        settings.mock_dir / "environment/currents.csv"
    )

    # WARNING: Unused variable (taken from the deprecated project)
    # delta_t: np.float64 = np.float64(
    #     settings.simulation.parameters.tref / len(currents_dataset)
    # )

    logger.success("Background simulation processing")

    data_lake_items = data_lake.anomaly_detections_for_simulation
    async for anomaly_detection in data_lake_items.consume():
        try:
            processes.run(
                namespace="simulation",
                key="process",
                callback=_process,
                anomaly_detection=anomaly_detection,
                currents_dataset=currents_dataset,
                leakages_dataset=leakages_dataset,
            )
            logger.debug(f"Simulation processing for {anomaly_detection.id}")
        except processes.ProcessErorr:
            logger.info(f"Skipping the simulation: {anomaly_detection.id}")
            continue

        # WARNING: Items are not adde to the data lake. Should we resolve that?

        # Update the data lake
        # WARNING: The object that stores into the data lake
        #          has the next amount of concentrations:
        #          total_concentrations = sum(leaks) * sum(currents)
        #          It might be a good idea to store the whole data into the
        #          database and save ids into the data lake.
        # data_lake.simulation_detections.storage.append(detections)


@transaction
async def _process(
    anomaly_detection: AnomalyDetection,
    currents_dataset: list[Current],
    leakages_dataset: list[Leakage],
):
    """The simulation processing entrypoint.
    This coroutine is running in the separate process.

    The last step of the processing is an estimation.
    """

    sensor: Sensor = await SensorsRepository().get(
        anomaly_detection.time_series_data.sensor_id
    )

    detections_uncommited: list[DetectionUncommited] = [
        plume2d.simulate(
            sensor=sensor,
            anomaly_detection=anomaly_detection,
            leakage=leakage,
            currents=currents_dataset,
        )
        for leakage in leakages_dataset
    ]

    # Save detections to the database
    detections: list[
        Detection
    ] = await SimulationDetectionsRepository().bulk_create(
        detections_uncommited
    )

    logger.debug(f"Simulation processing for {anomaly_detection.id} is done")

    # TODO: Start the estimation process

    return detections
