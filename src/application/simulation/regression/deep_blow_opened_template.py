import numpy as np

from src.config import settings
from src.domain.currents import Current
from src.domain.sensors import Sensor
from src.domain.simulation import CartesianCoordinates, DetectionRate, Leakage
from src.domain.templates.models import Template
from src.infrastructure.physics import constants


def calculate_time_to_reach_sensor(
    coordinates: CartesianCoordinates, current: Current
) -> np.float32:
    R = coordinates.x
    # Johansen (2022) uses this R instead:
    # R = sqrt(sensor.x_transformed * sensor.x_transformed + sensor.y_transformed * sensor.y_transformed)
    return np.float32(R / current.magnitude)


def calculate_plume_rise(
    leakage: Leakage, u: np.float32, t: np.float32
) -> np.float32:
    """Reference values for u and t from johansen (2022), p.9"""

    parameters = settings.simulation.parameters

    uref = parameters.uref
    tref = parameters.tref

    # TODO: Check units in old application for this case
    # ----------------------------------------------------

    u_hat = (u / uref) ** parameters.p  # convert uref to m/s
    t_hat = (t / tref) ** parameters.q

    return np.float32(leakage.z + parameters.a * u_hat * t_hat)


def calculate_plume_width(
    leakage: Leakage,
    current: Current,
    t_sensor: np.float32,
    plume_rise: np.float32,
    Cd: np.float32,
) -> np.float32:
    parameters = settings.simulation.parameters

    # The solved integral (Eq.(8)) can now be computed:
    I = leakage.z * t_sensor + (t_sensor * (plume_rise - leakage.z)) / (
        1 + parameters.q
    )

    # Now we can compute sigma_d (squared) from the leak model
    kappa = parameters.kappa
    f = np.sqrt(Cd)  # Friction factor
    u_f = f * current.magnitude  # Friction velocity

    sigma_d_sq = 2 * kappa * u_f * I  # Eq.(7) in Johansen (2022)

    # NOTE: In the early stages of the plume rise, the plume expansion
    #       can be dominated by entrainment due to internal plume turbulence.
    #       To account for this we might express sigma as a root-squared
    #       sum of the radius b from the plume model and
    #       the radius sigma_d from the turbulent diffusion model.
    #       That is, sigma = sqrt( (b/2)^2 + sigma_d^2). b is divided by 2
    #       to account for the difference in the definintion
    #       of the characteristic radius in the two models.
    #       Eq.(10) in Johansen (2022)

    # Calculate plume model radius
    # from Øistein Johansens Excel sheet (Tor II)
    b = parameters.alpha * (plume_rise - leakage.z)
    sigma_sq = (b / 2) ** 2 + sigma_d_sq

    return sigma_sq


def get_concentration(
    sensor: Sensor,
    leakage: Leakage,
    current: Current,
    coordinates: CartesianCoordinates,
    Cd: np.float32,
) -> np.float32:
    # First find the time it takes for the plume to reach the sensor
    t_sensor: np.float32 = calculate_time_to_reach_sensor(
        coordinates=coordinates, current=current
    )

    # NOTE: If the sensor is `behind` the leak, or the current is zero
    # so the leak won't be detected
    if t_sensor <= 0 or current.magnitude == 0.0:
        return np.float32(0)

    # Calculate the plume rise and the characteristic radius of the plume
    z_plume = calculate_plume_rise(
        leakage=leakage, u=current.magnitude, t=t_sensor
    )
    sigma_sq = calculate_plume_width(
        leakage=leakage,
        current=current,
        t_sensor=t_sensor,
        plume_rise=z_plume,
        Cd=Cd,
    )

    # Calculate the centerline concentration, C0 (See Johansen(2022) p.10)
    C0 = leakage.rate / (2 * constants.PI * current.magnitude * sigma_sq)

    # Compute the distance r from the centerline to the sensor
    delta_y = coordinates.y
    delta_z = sensor.z - z_plume
    r_sq = (delta_y * delta_y) + (delta_z * delta_z)
    # r = sqrt(r_sq)

    # Compute the concentration at a distance r from the centerline, i.e.
    # the concentration at the center
    C = C0 * np.exp(-r_sq / (2 * sigma_sq))

    return C  # kg/m3
