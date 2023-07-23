"""
This module includes the subsea environmental utils
that are used by the detection rates processing.
"""
import numpy as np

from src.config import settings
from src.domain.currents import Current
from src.domain.waves import Wave
from src.infrastructure.physics import constants


def get_wave_drag_coefficient(
    wave: Wave, current: Current, radians=True
) -> np.float64:
    """Wrapper for the actual calculation.
    Ub - Current speed in cm/s
    Db - Current direction, degrees or radians
    Hs - Significant wave height i meters
    Tp - Peak wave period in seconds
    DD - Wave direction, degrees or radians
    depth - Water depth in meters

    💩 This piece of a code is quite shitty. Need to be refactored.
    """

    Ub: np.float64 = current.magnitude * 100  # meter to centimeter
    Db: np.float64 = current.angle_from_north
    Hs: np.float64 = wave.height
    Tp: np.float64 = wave.period
    DD: np.float64 = wave.angle_from_north
    depth: np.float64 = settings.simulation.parameters.depth

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
