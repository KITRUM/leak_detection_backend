import numpy as np
from loguru import logger

from src.application.data_lake import data_lake
from src.application.simulation import regression
from src.config import settings
from src.domain.currents import Current
from src.domain.currents import services as currents_services
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.simulation import CartesianCoordinates, DetectionRate, Leakage
from src.domain.simulation import services as simulation_services
from src.domain.simulation.types import RegressionProcessor
from src.domain.templates import Template
from src.domain.waves import Wave
from src.domain.waves import services as waves_services
from src.infrastructure.errors import UnprocessableError
from src.infrastructure.physics import constants

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


def _get_regression_processor_callback(
    template: Template,
) -> RegressionProcessor:
    if template.z_roof is None:
        return regression.deep_blow_opened_template.get_concentration
    else:
        raise NotImplementedError(
            "Only opened template deep blow regression is available"
        )


def get_wave_drag_coefficient(
    wave: Wave, current: Current, radians=True
) -> np.float32:
    """Wrapper for the actual calculation.
    Ub - Current speed in cm/s
    Db - Current direction, degrees or radians
    Hs - Significant wave height i meters
    Tp - Peak wave period in seconds
    DD - Wave direction, degrees or radians
    depth - Water depth in meters
    """

    Ub: np.float32 = current.magnitude * 100  # meter to centimeter
    Db: np.float32 = current.angle_from_north
    Hs: np.float32 = wave.height
    Tp: np.float32 = wave.period
    DD: np.float32 = wave.angle_from_north
    depth: np.float32 = settings.simulation.parameters.depth

    # Constants, defined in the "Parameters" tab of
    # Øistein's excel sheet on wave data
    T_deep = np.sqrt(4 * constants.PI * depth / constants.G)

    # Variables corresponding to columns in the "Waves and currents" tab
    # of Øistein's excel sheet
    seabed = Tp > T_deep  # TODO: NOTE: Unused variable
    omega = 2 * constants.PI / Tp
    k_1 = omega**2 / constants.G
    k_2 = k_1 / np.tanh(k_1 * depth)
    k_3 = k_1 / np.tanh(k_2 * depth)
    k = k_1 / np.tanh(k_3 * depth)
    Ubw = 100 * constants.H_FAC * omega * Hs / np.sinh(k * depth)
    Tau_b = constants.ROW * constants.CD * (0.01 * Ub) ** 2
    Ustar = np.sqrt(Tau_b / constants.ROW) * 100  # NOTE: Unused variable
    if radians:
        # Input is in radians, do not convert
        cos_fi = -(np.cos(Db) * np.cos(DD) + np.sin(Db) * np.sin(DD))
    else:
        # Input is in degrees, convert to radians
        cos_fi = -(
            np.cos(np.radians(Db)) * np.cos(np.radians(DD))
            + np.sin(np.radians(Db)) * np.sin(np.radians(DD))
        )

    # Iterative process starts here
    # Refactoring from repeated columns in Excel to a loop
    # WARNING: This loop is overwriting itself.
    # TODO: Reduce the complexity
    # TODO: Investigate why 6 is here! (Leakages number?)
    for i in range(6):
        if i == 0:
            # Setting initial values here
            my = 0
            Cmy = 1
        else:
            my = Tau_b / tau_wm
            Cmy = np.sqrt(1 + 2 * my * np.abs(cos_fi) + my**2)

        fwc = Cmy * np.exp(
            5.61 * (Cmy * 0.01 * Ubw / (constants.KN * omega)) ** (-0.109)
            - 7.3
        )
        tau_wm = 0.5 * constants.ROW * fwc * (0.01 * Ubw) ** 2

    # After iterating five times, do some additional computations
    A = np.exp(
        2.96 * (Cmy * 0.01 * Ubw / (constants.KN * omega)) ** (-0.071) - 1.45
    )
    d_wc = A * constants.KAPPA / omega * np.sqrt(Cmy * tau_wm / constants.ROW)
    Z0_w = d_wc * (30 * d_wc / constants.KN) ** (-np.sqrt(my / Cmy))
    Cdw = (constants.KAPPA / np.log(constants.Z_REF / Z0_w)) ** 2
    Cd_corr = max(constants.CD, Cdw)

    # NOTE: Redundant calculations
    # Uf = np.sqrt(Cd)*0.01*Ub
    # Ufw = np.sqrt(Cdw)*0.01*Ub

    return Cd_corr


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
            _get_regression_processor_callback(sensor.template)
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

        return rates
