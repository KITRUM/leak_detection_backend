"""
The purpose of this module is reflecting the general idea
of the simulation processing that producing the detection rates
"""

import numpy as np
from numpy.typing import NDArray

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.currents import Current
from src.domain.currents import services as currents_services
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.simulation import (
    CartesianCoordinates,
    Detection,
    Leakage,
    RegressionProcessor,
    SimulationDetectionRateInDb,
    SimulationDetectionRateUncommited,
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


def get_detection(
    sensor: Sensor,
    leakage: Leakage,
    currents: list[Current],
    waves: list[Wave],
) -> Detection:
    concentrations: NDArray[np.float64] = np.zeros(
        len(currents), dtype=np.float64
    )

    for index, (current, wave) in enumerate(zip(currents, waves)):
        # Calculate wave-enhanced drag coefficient
        Cd: np.float64 = (
            get_wave_drag_coefficient(wave=wave, current=current)
            if settings.simulation.options.wave_current_interaction is True
            else np.float64(0)
        )

        transformed_coordinates: CartesianCoordinates = (
            get_sensor_transformed_coordinates(sensor, leakage, current)
        )

        regression_processor: RegressionProcessor = (
            regression_dispatcher.get_processor_callback(sensor.template)
        )

        concentration: np.float64 = regression_processor(
            sensor=sensor,
            leakage=leakage,
            current=current,
            coordinates=transformed_coordinates,
            Cd=Cd,
        )

        concentrations[index] = concentration

    return Detection(
        sensor=sensor, leakage=leakage, concentrations=concentrations
    )


async def process():
    """Consume fetched anomaly detection from data lake and run the simulation.
    The result is produced back to data lake and saved
    to the database for making the history available.

    WARNING: files are loaded only once for the whole processing

    WARNING: Wave and currents datasets should have the same amount of values,
             since it is required by the processing algorithm.
    """

    # NOTE: Skip if settings are set
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
    waves_dataset: list[Wave] = waves_services.load_waves_dataset(
        settings.mock_dir / "environment/waves.csv"
    )
    currents_dataset: list[Current] = currents_services.load_currents_dataset(
        settings.mock_dir / "environment/currents.csv"
    )

    if len(waves_dataset) != len(currents_dataset):
        raise UnprocessableError(
            message=(
                "Waves and currents seed files have "
                "different number of columns"
            )
        )

    # WARNING: Unused variable (taken from the deprecated project)
    # delta_t: np.float64 = np.float64(
    #     settings.simulation.parameters.tref / len(currents_dataset)
    # )

    async for anomaly_detection in data_lake.anomaly_detections.consume():
        sensor: Sensor = await SensorsRepository().get(
            anomaly_detection.time_series_data.sensor_id
        )

        detections: list[Detection] = [
            get_detection(
                sensor=sensor,
                leakage=leakage,
                currents=currents_dataset,
                waves=waves_dataset,
            )
            for leakage in leakages_dataset
        ]

        # ------------------------------------------------
        # ========== Detection rates processing ==========
        # ------------------------------------------------
        simulation_detection_rates: list[SimulationDetectionRateInDb] = []
        for detection in detections:
            above_limit = np.zeros(detection.concentrations.shape)
            above_limit[
                np.where(
                    detection.concentrations
                    > settings.simulation.parameters.detection_limit
                )
            ] = 1

            schema = SimulationDetectionRateUncommited(
                anomaly_detection_id=anomaly_detection.id,
                concentrations=",".join(
                    str(el) for el in detection.concentrations
                ),
                leakage=detection.leakage.flat_dict(),
                rate=float(np.sum(above_limit) / np.size(above_limit)),
            )

            # TODO: change to batch save all detections
            instance: SimulationDetectionRateInDb = (
                await (
                    simulation_services.save_simulation_detection_rate(schema)
                )
            )

            simulation_detection_rates.append(instance)

        # Update the data lake
        # WARNING: The object that stores into the data lake
        #          has the next amount of concentrations:
        #          total_concentrations = sum(leaks) * sum(currents)
        #          It might be a good idea to store the whole data into the
        #          database and save ids into the data lake.
        data_lake.simulation_detection_rates.storage.append(
            simulation_detection_rates
        )
