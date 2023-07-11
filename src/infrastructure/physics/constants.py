import numpy as np

G = 9.81  # Acceleration of gravity
ROW = 1025  # Density of seawater
KN = 0.025
H_FAC = 0.5 / np.sqrt(2)
KAPPA = 0.41
Z_0 = KN / 30
Z_REF = 3
CD = (KAPPA / np.log(Z_REF / Z_0)) ** 2
PI = np.pi
P_ATM = 101325.0  # Atmospheric pressure in Pa
MW = 0.018  # molar mass of water (kg/mol)
MG = 0.016  # molar mass of methane (kg/mol)
