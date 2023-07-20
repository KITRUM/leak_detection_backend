"""
The purpose of this module is reflecting the general idea
of the simulation processing that producing the detection rates
"""

import numpy as np

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.currents import Current
from src.domain.currents import services as currents_services
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.simulation import (
    CartesianCoordinates,
    DetectionRate,
    Leakage,
    RegressionProcessor,
)
from src.domain.simulation import services as simulation_services
from src.domain.waves import Wave
from src.domain.waves import services as waves_services
from src.infrastructure.errors import UnprocessableError
from src.infrastructure.physics import constants

from .regression import dispatcher as regression_dispatcher
from .subsea import get_wave_drag_coefficient

__all__ = ("process",)


def get_sensor_transformed_coordinates(
    sensor: Sensor, leak: Leakage, current: Current
) -> CartesianCoordinates:
    """Transforms the (x,y)-coordinates to fit into a cartesian coordinate system where:
    - The leak is at the origin in the (x,y)-plane
    - The x-axis points along the direction of the current
    """
    # Rotate the coordinates so that the x-axis points along the direction of the current
    rotate_angle = (
        current.angle_from_north
        - constants.PI / 2
        - sensor.template.angle_from_north
    )
    alpha = np.cos(rotate_angle)
    beta = np.sin(rotate_angle)

    coordinates = CartesianCoordinates(
        x=np.float32(sensor.x * alpha - sensor.y * beta),
        y=np.float32(sensor.x * beta + sensor.y * alpha),
    )

    transformed_leak_x = np.float32(leak.x * alpha - leak.y * beta)
    transformed_leak_y = np.float32(leak.x * beta + leak.y * alpha)

    # Shift the coordinates so that the origin is at the leak
    coordinates.x -= transformed_leak_x
    coordinates.y -= transformed_leak_y

    return coordinates


def get_detection_rate(
    sensor: Sensor,
    leakage: Leakage,
    currents: list[Current],
    waves: list[Wave],
) -> DetectionRate:
    rate = DetectionRate(sensor=sensor, leakage=leakage)

    for current, wave in zip(currents, waves):
        # Calculate wave-enhanced drag coefficient
        Cd: np.float32 = (
            get_wave_drag_coefficient(wave=wave, current=current)
            if settings.simulation.options.wave_current_interaction is True
            else np.float32(0)
        )

        transformed_coordinates: CartesianCoordinates = (
            get_sensor_transformed_coordinates(sensor, leakage, current)
        )

        regression_processor: RegressionProcessor = (
            regression_dispatcher.get_processor_callback(sensor.template)
        )

        concentration: np.float32 = regression_processor(
            sensor=sensor,
            leakage=leakage,
            current=current,
            coordinates=transformed_coordinates,
            Cd=Cd,
        )
        rate.concentrations.append(concentration)

    return rate


async def process():
    """Consume fetched anomaly detection from data lake and run the simulation.
    The result is produced back to data lake and saved
    to the database for making the history available.

    WARNING: files are loaded only once for the whole processing

    WARNING: Wave and currents datasets should have the same amount of values,
             since it is required by the processing algorithm.
    """

    leakages_dataset: list[
        Leakage
    ] = simulation_services.load_leakages_dataset(
        settings.mock_dir / "simulated_leakages.csv"
    )
    waves_dataset: list[Wave] = waves_services.load_waves_dataset(
        settings.mock_dir / "environment/waves.csv"
    )
    currents_dataset: list[Current] = currents_services.load_currents_dataset(
        settings.mock_dir / "environment/currents.csv"
    )

    if len(waves_dataset) != len(currents_dataset):
        raise UnprocessableError(
            message="Waves and currents seed files have different number of columns"
        )

    # WARNING: Unused variable
    delta_t: np.float32 = np.float32(
        settings.simulation.parameters.tref / len(currents_dataset)
    )

    # type is AnomalyDetection
    async for anomaly_detection in data_lake.anomaly_detections.consume():
        if settings.debug is False:
            raise NotImplementedError(
                "Currently the simulation is not working with real data"
            )

        if settings.simulation.options.run_open_template is False:
            raise NotImplementedError(
                "Closed template simulation is not implemented yet"
            )

        sensor: Sensor = await SensorsRepository().get(
            anomaly_detection.time_series_data.sensor_id
        )

        rates: list[DetectionRate] = [
            get_detection_rate(
                sensor=sensor,
                leakage=leakage,
                currents=currents_dataset,
                waves=waves_dataset,
            )
            for leakage in leakages_dataset
        ]

        # Update the data lake
        # WARNING: The object that stores into the data lake
        #          has the next amount of concentrations:
        #          total_concentrations = sum(leaks) * sum(currents)
        #          It might be a good idea to store the whole data into the
        #          database and save ids into the data lake.
        data_lake.detection_rates_by_sensor[sensor.id].storage.append(rates)