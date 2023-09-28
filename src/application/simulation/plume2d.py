import copy
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numpy.typing import NDArray

from src.config import settings
from src.domain.anomaly_detection import AnomalyDetection
from src.domain.currents.models import Current
from src.domain.sensors import Sensor
from src.domain.simulation import DetectionUncommited, Leakage


def kelvin(degree) -> float:
    # return np.float64(degree+273.0)
    return degree + 273.0


# TODO: Move to the config file
class EnvironmentParameters:
    """This class includes the simulation configuration.
    Just for the sake of simplicity, we will use a single
    class to represent the simulation configuration.
    Just create another attribute if you need to add
    another configuration.
    """

    _H = 90.0  # water depth [m]
    _T_w = 6.0  # water temperature [deg. C]
    _gor = 55.0  # gas-to-oil ration [m^3_gas / m^3_oil] at std. conditions
    _rho_g = 0.9  # org. rog_ref; reference density of gas [k/m^3] at std. conditions
    _rho_o = 850.0  # org. roil; density of oil [kg/m^3]

    ad_0 = 28.192  # seawater density sigma [kg/m^3]
    ad_1 = -0.07137  # seawater density sigma [kg/m^3]
    ad_2 = -0.004863  # seawater density sigma [kg/m^3]
    av_0 = 1.836  # seawater kinematic viscosity sigma [10^-6 m^2/s]
    av_1 = -0.05491  # seawater kinematic viscosity sigma [10^-6 m^2/s]
    av_2 = 0.000772  # seawater kinematic viscosity sigma [10^-6 m^2/s]
    adiff_0 = 0.6876  # coefficient of diffusivity of gas (i.e. methane) in water [10^-9 m^2/s]
    adiff_1 = 0.0332  # coefficient of diffusivity of gas (i.e. methane) in water [10^-9 m^2/s]
    adiff_2 = 0.0  # coefficient of diffusivity of gas (i.e. methane) in water [10^-9 m^2/s]
    rho_g_diss = 300.0  # apparent density of dissolved gas fractions [kg/m^3]
    aH_0 = 23.9  # Henri's constant sigma [atm/(kg/m^3)]
    aH_1 = 0.805  # Henri's constant sigma [atm/(kg/m^3)]
    gamma = 1.224  # Salting coefficient for std. seawater (s = 35 ppt)

    H_0 = 10.0  # standard depth of the water column corresponding to 1 atm standard pressure
    T_0 = 15.0  # org. t_ref; standard reference temperature
    g_atm = 9.81  # gravity [m/s^2] in std. conditions
    kappa = 0.4  # von-Karman constant
    IFT_g = 70.0  # interfacial tension gas-water [mN/m]
    IFT_o = 20.0  # interfacial tension oil-water [mN/m]

    _rho_w = 0.0  # seawater density [kg/m^3]
    _visc_w = 0.0  # kinematic viscosity of seawater [m^2/s]
    _diff_w = 0.0  # diffusivity of gas in seawater [m^2]
    _Sc = 0.0  # Schmidt number
    _g_o_red = 0.0  # reduced gravity [m/s^2] for oil droplets

    # refactor information: the following passage are per-run variables and do not need to be class variables
    _H_w = 0.0  # or.g Hsw; Henri's constant at sea temperature [atm/(kg/m^3)]

    @property
    def H(self):
        return self._H

    @property
    def T_w(self):
        return self._T_w

    @property
    def gor(self):
        return self._gor

    @property
    def rho_g(self):
        return self._rho_g

    @property
    def rho_o(self):
        return self._rho_o

    @property
    def rho_w(self):
        return self._rho_w

    @property
    def visc_w(self):
        return self._visc_w

    @property
    def diff_w(self):
        return self._diff_w

    @property
    def schmidt_coeff(self):
        return self._Sc

    @property
    def H_w(self):
        return self._H_w

    @property
    def g_o_reduced(self):
        return self._g_o_red

    def __init__(self, depth=90.0, temperature=6.0):
        self._H = depth
        self._T_w = temperature
        self._gor = 55.0
        self._rho_g = 0.9
        self._rho_o = 850.0
        self.ad_0 = 28.192
        self.ad_1 = -0.07137
        self.ad_2 = -0.004863
        self.av_0 = 1.836
        self.av_1 = -0.05491
        self.av_2 = 0.000772
        self.adiff_0 = 0.6876
        self.adiff_1 = 0.0332
        self.adiff_2 = 0.0
        self.rho_g_diss = 300.0
        self.aH_0 = 23.9
        self.aH_1 = 0.805
        self.gamma = 1.224
        self.H_0 = 10.0
        self.T_0 = 15.0
        self.g_atm = 9.81
        self.kappa = 0.4
        self.IFT_g = 70.0
        self.IFT_o = 20.0
        self._rho_w = (
            1000
            + self.ad_0
            + self.ad_1 * self._T_w
            + self.ad_2 * math.pow(self._T_w, 2)
        )
        self._visc_w = 0.000001 * (
            self.av_0
            + self.av_1 * self._T_w
            + self.av_2 * math.pow(self._T_w, 2)
        )
        self._diff_w = 0.000000001 * (
            self.adiff_0
            + self.adiff_1 * self._T_w
            + self.adiff_2 * math.pow(self._T_w, 2)
        )
        self._Sc = self._visc_w / self._diff_w
        self._g_o_red = self.g_atm * (self._rho_w - self._rho_o) / self._rho_w
        self._H_w = self.gamma * (self.aH_0 + self.aH_1 * self._T_w)

    def __repr__(self):
        outstring = "(\nEnvironmentParameters:\n\tH: {:g}\n\tT_w: {:g}\n\tGOR: {:g}\n".format(
            self._H, self._T_w, self._gor
        )
        outstring += "\trho_g: {:g}\n\trho_o: {:g}\n\tad_0: {:g}\n\tad_1: {:g}\n\tad_2: {:g}\n".format(
            self._rho_g, self._rho_o, self.ad_0, self.ad_1, self.ad_2
        )
        outstring += "\tav_0: {:g}\n\tav_1: {:g}\n\tav_2: {:g}\n".format(
            self.av_0, self.av_1, self.av_2
        )
        outstring += (
            "\tadiff_0: {:g}\n\tadiff_1: {:g}\n\tadiff_2: {:g}\n".format(
                self.adiff_0, self.adiff_1, self.adiff_2
            )
        )
        outstring += "\trho_g_diss: {:g}\n\tgamma: {:g}\n".format(
            self.rho_g_diss, self.gamma
        )
        outstring += "\taH_0: {:g}\n\taH_1: {:g}\n".format(
            self.aH_0, self.aH_1
        )
        outstring += "\tH_0: {:g}\n\tT_0: {:g}\n\tg_atm: {:g}\n".format(
            self.H_0, self.T_0, self.g_atm
        )
        outstring += "\tkappa: {:g}\n\tIFT_g: {:g}\n\tIFT_o: {:g}\n".format(
            self.kappa, self.IFT_g, self.IFT_o
        )
        outstring += "\trho_w: {:g}\n\tvisc_w: {:g}\n\tdiff_w: {:g}\n".format(
            self._rho_w, self._visc_w, self._diff_w
        )
        outstring += (
            "\tSchmidt: {:g}\n\tg_o_reduced: {:g}\n\tH_w: {:g}\n".format(
                self._Sc, self._g_o_red, self._H_w
            )
        )
        outstring += ")"
        return outstring


class Plume:
    _phi_0 = (
        0.0  # angular exit direction [arcdeg]; ref: clockwise from vertical
    )
    _d_0 = 3.0  # exit diameter [mm]; optionally replaced by computation
    _q_gas = (
        7.1  # volumetric gas flow [L/min] at bottom pressure & temperature
    )

    D_lim = 0.003  # limiting droplet- and bubble diameter [m]
    Cdp = 0.4  # droplet- and bubble drag coefficient

    _rho_g_0 = 0.0  # org. rog_0; gas density at discharge depth [kg/m^3]
    _Q_g_0 = 0.0  # volume flow of gas [m^3/s]
    _Q_o_0 = 0.0  # volume flow of oil [m^3/s]
    _Q_tot = 0.0  # total volume flow
    _G_g_0 = 0.0  # mass flow rate of gas [kg/s]
    _G_o_0 = 0.0  # mass flow rate of oil [kg/s]
    _G_tot = 0.0  # total mass flow
    _rho_mix_0 = 0.0  # org. rom_0; mixed density [kg/m^3]
    # _d_out_def = 0.     # prescribed exit diameter [m]
    # _d_calc = 0.         # computed exit diameter [m]
    _d_out = 0.0  # org. d0 (Initialization:K17); output exit diameter; either _d_out_def or _d_calc;
    # depending on opt_d

    # refactor information: the following passage are per-run variables and do not need to be class variables
    # following parameters are dynamic at runtime, as they depend on the time step
    _v_0 = 0.0  # exit velocity (i.e. speed) [m/s]
    _g_out_red = 0.0  # reduced gravity for the outlet flow [m/s^2]
    _F_moment = 0.0  # kinematic momentum flux [m^4/s^2]; temporary var
    _F_bouy = 0.0  # buoyancy flux [m^4/s^3]; temporary var
    _L_moment = 0.0  # org. L_m; momentum length [m]
    _froude = 0.0  # Froude number
    _v_adjust = 0.0  # adjusted velocity [m/s]; temporary var
    _D_g_init = 0.0  # initial gas bubble diameter [m]
    _D_o_init = 0.0  # initial oil droplet diameter [m]

    A_We = 28.0  # coefficient A in Weber correlation
    We_x = 3240.0  # exit Weber number
    _weber = 0.0  # Weber number

    _v_stokes = 0.0  # stokes law - computed by simulation (depth-dependent)
    _v_drag = (
        0.0  # constant drag law - set computed simulation (depth-dependent)
    )
    _Uzz_o_init = 0.0  # org. Uoil_init; rise velocity (i.e. z-component of z-velocity of flux U) of oil droplets
    # - computed by simulation

    _sol = 0.0  # org. Slb; discharge-depth solubility [kg/m^3] - set by simulation (depth-dependent)
    _r_sol_rho_g = 0.0  # org. Srog; ratio of solubility-to-density - set by simulation in concert with _sol

    @property
    def phi_0(self):
        return self._phi_0

    @phi_0.setter
    def phi_0(self, value):
        self._phi_0 = value

    @property
    def d_0(self):
        return self._d_0

    @d_0.setter
    def d_0(self, value):
        self._d_0 = value

    @property
    def q_gas(self):
        return self._q_gas

    @q_gas.setter
    def q_gas(self, value):
        self._q_gas = value

    @property
    def rho_g_0(self):
        return self._rho_g_0

    @property
    def Q_g_0(self):
        return self._Q_g_0

    @property
    def Q_o_0(self):
        return self._Q_o_0

    @property
    def Q_tot(self):
        return self._Q_tot

    @property
    def G_g_0(self):
        return self._G_g_0

    @property
    def G_o_0(self):
        return self._G_o_0

    @property
    def G_tot(self):
        return self._G_tot

    @property
    def rho_mix_0(self):
        return self._rho_mix_0

    @property
    def d_out(self):
        return self._d_out

    @property
    def v_0(self):
        return self._v_0

    @property
    def g_out_reduced(self):
        return self._g_out_red

    @property
    def L_moment(self):
        return self._L_moment

    @property
    def froude(self):
        return self._froude

    @property
    def weber(self):
        return self._weber

    @property
    def D_g_init(self):
        return self._D_g_init

    @property
    def D_o_init(self):
        return self._D_o_init

    @property
    def Uzz_o_init(self):
        return self._Uzz_o_init

    @property
    def solubility(self):
        return self._sol

    @property
    def r_sol_rho_g(self):
        return self._r_sol_rho_g

    # Dev-Comment: 'Plume' is part of the 'Simulation', so 'Plume' cannot access member variables of 'Simulation'.
    # Hence, those quantities need to be then provided as parameters, where needed.
    # 'Environment' is a sibling (input-)class to 'Plume' and thus can be provided as input object.
    # 'Environment' is not to be stored, but only used by reference as parameter.
    def __init__(self, env_param: EnvironmentParameters, z_0=1.4):
        self._z_0 = z_0
        self._phi_0 = 0.0
        self._d_0 = 3.0
        self._q_gas = 7.1
        self.D_lim = 0.003
        self.Cdp = 0.4
        self.A_We = 28.0
        self.We_x = 3240.0

        self._rho_g_0 = (
            env_param.rho_g
            * (
                (env_param.H + env_param.H_0 - self._z_0)
                * kelvin(env_param.T_0)
                / kelvin(env_param.T_w)
            )
            / env_param.H_0
        )  ### I have not found z0++++++++++++++++
        self._Q_g_0 = (
            0.001 * self._q_gas / 60.0
        )  # conversion from L/min to m^3/s
        self._G_g_0 = self._Q_g_0 * self._rho_g_0
        self._G_o_0 = (self._G_g_0 * env_param.rho_o) / (
            env_param.rho_g * env_param.gor
        )  ####It seems like self._rho_g_0 is missing++++++++++++++
        self._Q_o_0 = self._G_o_0 / env_param.rho_o
        self._Q_tot = self._Q_g_0 + self._Q_o_0
        self._G_tot = self._G_g_0 + self._G_o_0
        self._rho_mix_0 = self._G_tot / self._Q_tot

    def __repr__(self):
        outstring = "(\nPlume:\n\tz_0: {:.3g}\n\tphi_0: {:.3g}\n\td_0: {:.3g}\n".format(
            self._z_0, self._phi_0, self._q_gas
        )
        outstring += "\tq_gas:{:g}\n\tD_lim: {:.3g}\n\tCdp: {:.3g}\n".format(
            self._q_gas, self.D_lim, self.Cdp
        )
        outstring += "\trho_g_0: {:g}\n\trho_mix_0: {:.3g}\n".format(
            self._rho_g_0, self._rho_mix_0
        )
        outstring += (
            "\tG_g_0: {:g}\n\tG_o_0: {:.3g}\n\tG_tot: {:.3g}\n".format(
                self._G_g_0, self._G_o_0, self._G_tot
            )
        )
        outstring += (
            "\tQ_g_0: {:g}\n\tQ_o_0: {:.3g}\n\tQ_tot: {:.3g}\n".format(
                self._Q_g_0, self._Q_o_0, self._Q_tot
            )
        )
        outstring += (
            "\td_out: {:.3g}\n\tv_0: {:.3g}\n\tg_out_reduced: {:.3g}\n".format(
                self._d_out, self._v_0, self._g_out_red
            )
        )
        outstring += "\tF_moment: {:.3g}\n\tF_bouyance: {:.3g}\n\tL_moment: {:.3g}\n".format(
            self._F_moment, self._F_bouy, self._L_moment
        )
        outstring += "\tfroude: {:.3g}\n\tv_adjust: {:.3g}\n".format(
            self._froude, self._v_adjust
        )
        outstring += (
            "\tA_We: {:.3g}\n\tWe_x: {:.3g}\n\tweber: {:.3g}\n".format(
                self.A_We, self.We_x, self._weber
            )
        )
        outstring += "\tD_g_init: {:.3g}\n\tD_o_init: {:.3g}\n".format(
            self._D_g_init, self._D_o_init
        )
        outstring += "\tv_stokes: {:.3g}\n\tv_drag: {:.3g}\n\tUzz_o_init: {:.3g}\n".format(
            self._v_stokes, self._v_drag, self._Uzz_o_init
        )
        outstring += "\tsolubility: {:.3g}\n\tr_sol_rho_g: {:.3g}\n)".format(
            self._sol, self._r_sol_rho_g
        )
        return outstring

    def compute_d_out(
        self, IFT_g, compute_weber=False
    ):  ##### when do we need to comute??? ++++++++++++++++
        self._d_out = self._d_0 * np.float64(0.001)
        if compute_weber:
            self._d_out = math.pow(
                (16.0 * self._rho_mix_0 * (self._Q_tot**2))
                / (self.We_x * (math.pi**2) * 0.001 * IFT_g),
                1.0 / 3.0,
            )
        return self._d_out

    def compute_v0(self):
        self._v_0 = (
            np.float64(4.0) * (self._Q_tot) / (math.pi * (self._d_out**2))
        )

    def compute_solubility(self, env_param: EnvironmentParameters):
        self._sol = (env_param.H + env_param.H_0 - self._z_0) / (
            env_param.H_0 * env_param.H_w
        )
        self._r_sol_rho_g = self._sol / self._rho_g_0

    def compute_stoke_n_drag(
        self, env_param: EnvironmentParameters, bottom_drag_coeff
    ):
        self._v_stokes = (
            env_param.g_o_reduced
            * math.pow(min(self._D_o_init, self.D_lim), 2.0)
            / (18.0 * env_param.visc_w)
        )
        self._v_drag = math.sqrt(
            4.0
            * env_param.g_o_reduced
            * min(self._D_o_init, self.D_lim)
            / (3.0 * bottom_drag_coeff)
        )
        self._Uzz_o_init = 1.0 / (
            (1.0 / self._v_stokes) + (1.0 / self._v_drag)
        )

    def compute_init_plume_params(self, env_param: EnvironmentParameters):
        self._g_out_red = (
            env_param.g_atm
            * (env_param.rho_w - self._rho_mix_0)
            / env_param.rho_w
        )
        self._F_moment = self._G_tot * self._v_0 / env_param.rho_w
        self._F_bouy = self._g_out_red * self._Q_tot
        self._L_moment = math.pow(self._F_moment, 3.0 / 4.0) / math.pow(
            self._F_bouy, 1.0 / 2.0
        )
        self._froude = self._L_moment / self._d_out
        self._v_adjust = self._v_0 * (1.0 + 1.0 / self._froude)
        self._weber = (
            self._rho_mix_0
            * (self._v_adjust**2)
            * self._d_out
            / (0.001 * env_param.IFT_g)
        )
        self._D_g_init = (
            self.A_We * self._d_out * math.pow(self._weber, -3.0 / 5.0)
        )
        self._D_o_init = self._D_g_init * math.pow(
            env_param.IFT_o / env_param.IFT_g, 3.0 / 5.0
        )


class SimulationPlume2D:
    _opt_d = True  # option to compute exit diameter; False: as defined, True: computed
    _opt_sep = True  # option to compute separation; False: omit, True: compute
    _opt_diss = (
        True  # option to compute dissolution; False: omit, True: compute
    )
    _opt_td = True  # option to compute turbulent difference; False: omit, True: compute

    _t_max = 300.0  # max. simulation time [s]
    _N = 1001  # time steps
    _out_interval = 10  # output interval
    _dt = 0.0  # simulation time increment - to be set / calculated on simulation time

    a_j = 0.25  # coefficient in momentum jet
    alpha = 0.1  # entrainment coefficient
    Cdb = 0.001  # bottom drag coefficient

    # refactor information: the following passage are per-run variables and do not need to be class variables

    _tau_calc = 0.0  # dimensionless time - shall be initialized on 'run'
    _lambda_calc = (
        0.0  # dimensionless distance - shall be initialized on 'run'
    )
    _v_init = 0.0  # initial velocity [m/s] - shall be initialized on 'run'
    _G_g_init = 0.0  # initial gas mass [kg]
    _G_o_init = 0.0  # initial oil mass [kg]
    _G_w_init = 0.0  # initial water mass [kg]

    _env_param = None
    _plume_data = None
    _verbose = False

    def __init__(
        self,
        plume_data: Plume | None = None,
        verbose: bool = False,
        z_0: np.float64 = np.float64(1.4),
        U_b: np.float64 = np.float64(0.00),
    ):
        self._opt_d = True
        self._opt_sep = True
        self._opt_diss = True
        self._opt_td = True
        self._verbose = verbose
        self._t_max = 300.0
        self._N = 1001
        self._out_interval = 10
        self._dt = 0.0
        self.a_j = 0.25
        self.alpha = 0.1
        self.Cdb = 0.001
        self.U_b = U_b
        self.z_0 = z_0

        self._env_param: EnvironmentParameters = EnvironmentParameters()
        if self._verbose:
            print("== Environmental Parameters after creation ==")
            print(self._env_param)
        self._plume_data: Plume = (
            Plume(self._env_param, z_0=self.z_0)
            if plume_data is None
            else plume_data
        )
        if self._verbose:
            print("== Plume after creation ==")
            print(self._plume_data)
        self._plume_data.compute_solubility(
            env_param=self._env_param
        )  # computed here as z_0 of plume may have changed
        if self._verbose:
            print("== Plume after solubility compute ==")
            print(self._plume_data)

    def __repr__(self):
        outstring = (
            "(\nSimulation:\nComputeD = {}\n\tComputeSeparation = {}\n".format(
                self._opt_d, self._opt_sep
            )
        )
        outstring += (
            "\tComputeDissolution = {}\n\tComputeTurbulence = {}\n".format(
                self._opt_diss, self._opt_td
            )
        )
        outstring += "\tt_max = {:g}\n\tN = {}\n\tout_interval = {}\n\tdt = {:g}\n".format(
            self._t_max, self._N, self._out_interval, self._dt
        )
        outstring += "\ta_j = {:g}\n\talpha = {:g}\n\tCdb = {:g}\n".format(
            self.a_j, self.alpha, self.Cdb
        )
        outstring += "\ttau = {:g}\n\tlambda = {:g}\n\tv_init = {:g}\n".format(
            self._tau_calc, self._lambda_calc, self._v_init
        )
        outstring += "\tG_g_init = {:g}\n\tG_o_init = {:g}\n\tG_w_init = {:g}\n)".format(
            self._G_g_init, self._G_o_init, self._G_w_init
        )
        return outstring

    def run(
        self,
        runtime=300.0,
        steps=-1,
        output_interval=-1,
        timedelta=None,
        compute_weber=False,
    ):
        self._t_max = runtime
        if timedelta is None:
            assert steps > 0
            odd_steps = math.remainder(steps, 2) > 0
            self._N = steps if odd_steps else steps + 1
            self._dt = float(self._t_max) / float(self._N - 1)
        else:
            assert timedelta > 0.0
            self._dt = np.float64(timedelta)
            self._N = int(self._t_max / self._dt) + 1
        self._out_interval = (
            min(1, int(self._N / 10))
            if output_interval < 0
            else output_interval
        )

        self._plume_data.compute_d_out(
            self._env_param.IFT_g, compute_weber=compute_weber
        )
        if self._verbose:
            print("== Plume after computing d_out ==")
            print(self._plume_data)
        self._plume_data.compute_v0()
        if self._verbose:
            print("== Plume after compute v0 ==")
            print(self._plume_data)
        self._calculate_init_sim_params_()
        if self._verbose:
            print("==============================================")
            print("== Simulation after initializing parameters ==")
        self._plume_data.compute_init_plume_params(self._env_param)
        if self._verbose:
            print("== Plume after computing initial plume parameters ==")
            print(self._plume_data)
        self._plume_data.compute_stoke_n_drag(self._env_param, self.Cdb)
        if self._verbose:
            print("== Plume after computing stokes- and drag coefficients ==")
            print(self._plume_data)
            print("== Simulation parameters after initialisation ==")
            print(self)

        g_atm = self._env_param.g_atm
        rho_w = self._env_param.rho_w
        rho_g = self._env_param.rho_g  # rog_ref
        rho_o = self._env_param.rho_o
        U_b = self.U_b
        t_i = self._dt
        phi_i = (
            self._plume_data.phi_0
        )  # direction of the plume [arcdeg]; column I
        rad_phi_i = math.radians(phi_i)
        v_i = self._v_init  # axial velocity [m/s]; column H
        u_i = v_i * math.sin(rad_phi_i)  # u [m/s]; column F
        w_i = v_i * math.cos(rad_phi_i)  # w [m/s]; column G
        s_i = v_i * t_i  # length of plume element [m]; column D
        x_i = s_i * math.sin(rad_phi_i)  # downstream distance [m]; column B
        z_i = self.z_0 + s_i * math.cos(
            math.radians(phi_i)
        )  # plume height above seabed [m]; column C
        if self._verbose:
            print("x_i = {:g}, z_i = {:g}, s_i = {:g}".format(x_i, z_i, s_i))
            print(
                "phi_i = {:g}, u_i = {:g}, w_i = {:g}, v_i = {:g}".format(
                    phi_i, u_i, w_i, v_i
                )
            )
        G_g_i = self._G_g_init  # free gas mass (in bubbles) [kg]; column O
        G_diss_i = 0.0  # dissolved gas mass [kg]; column R
        G_o_i = self._G_o_init  # oil mass [kg]; column P
        G_w_i = self._G_w_init  # water mass [kg]; column Q
        G_tot_i = G_g_i + G_diss_i + G_o_i + G_w_i  # total mass [kg]; column S
        rho_g_i = (
            self._plume_data.rho_g_0
        )  # initial gas bubble density [kg/m^3]; column X
        Q_g_i = G_g_i / rho_g_i  # free gas volume (in bubbles) [m^3]; column J
        Q_diss_i = (
            G_diss_i / self._env_param.rho_g_diss
        )  # dissolved gas volume (in seawater) [m^3]; column M
        Q_o_i = G_o_i / self._env_param.rho_o  # oil volume [m^3]; column K
        Q_w_i = G_w_i / self._env_param.rho_w  # water volume [m^3]; column L
        Q_tot_i = (
            Q_g_i + Q_diss_i + Q_o_i + Q_w_i
        )  # total volume [m^3]; column N
        b_i = math.sqrt(
            Q_tot_i / (math.pi * s_i)
        )  # plume radius [m]; column E - SEMANTIC ERROR: plume diameter
        if self._verbose:
            print(
                "b_i = {:g}; s_i = {:g}; Q_tot_i = {:g}".format(
                    b_i, s_i, Q_tot_i
                )
            )
        D_g_i = (
            self._plume_data.D_g_init
        )  # initial gas bubble diameter (size); column W
        D_o_i = self._plume_data.D_o_init  # initial oil droplet diameter
        M_x_i = (
            G_tot_i * u_i
        )  # lateral momentum [kg*m/s] in xy-plane; column U
        M_z_i = (
            G_tot_i * w_i
        )  # vertical momentum [kg*m/s] in xz-plane; column V
        # Entrainment
        E_s = (
            2.0
            * math.pi
            * self.alpha
            * b_i
            * s_i
            * (v_i - (U_b * math.sin(rad_phi_i)))
            * rho_w
            * self._dt
        )  # shear entrainment [kg]; column Y
        E_f = (
            2.0 * b_i * s_i * (U_b * math.cos(rad_phi_i)) * rho_w * self._dt
        )  # force entrainment [kg]; column Z
        K = (
            self._env_param.kappa * math.sqrt(self.Cdb) * U_b * z_i
        )  # Karman value [m^2/s]; column AA
        E_t = (
            8.0 * math.pi * K * s_i * rho_w * self._dt if self._opt_d else 0.0
        )  # turbulence entrainment [kg]; column AB
        E = max(E_s, E_f, E_t)  # total entrainment [kg]; column AC
        # Gas bubble velocity
        g_g_i_reduced = (
            g_atm * (rho_w - rho_g_i) / rho_w
        )  # reduced gravity of the gas plume [m/s^2]; column AD
        Uzz_o_i = (
            self._plume_data.Uzz_o_init
        )  # initial oil droplet rise velocity (magnitude)
        Uxx_g_i = (
            g_g_i_reduced * (D_g_i * D_g_i) / (18.0 * self._env_param.visc_w)
        )  # org. uS; lateral flow velocity [m/s]; column AE
        U_C_g_i = math.sqrt(
            4.0 * g_g_i_reduced * D_g_i / (3.0 * self._plume_data.Cdp)
        )  # org. uC [m/s]; column AF
        U_g_b_i = (
            1.0 / (1.0 / Uxx_g_i + 1.0 / U_C_g_i) if D_g_i > 0.0 else 0.0
        )  # org. ugb [m/s]; column AG
        # Dissolution
        Re = U_g_b_i * D_g_i / self._env_param.visc_w  # Re; column AM
        k_i = (
            self._env_param.diff_w
            * (
                2.0
                + 0.6
                * math.pow(Re, 0.5)
                * math.pow(self._env_param.schmidt_coeff, 1.0 / 3.0)
            )
            / D_g_i
            if D_g_i > 0.0
            else 0.0
        )  # kappa [m/s]; column AN
        if self._verbose:
            print(
                "K = {:.4g}; D_w = {:.4g}; Reynolds = {:.4g}, Schmidt = {:.4g}, Dgas = {:.4g}".format(
                    k_i,
                    self._env_param.diff_w,
                    Re,
                    self._env_param.schmidt_coeff,
                    D_g_i,
                )
            )
        dG_g_i = (
            -6.0
            * k_i
            * G_g_i
            * self._plume_data.r_sol_rho_g
            * self._dt
            / D_g_i
            if D_g_i > 0.0
            else 0.0
        )  # org. dGgas, difference of gas mass [kg]; column AO
        dD_g_i = (
            (D_g_i / 3.0) * dG_g_i / G_g_i
        )  # org. dDb; difference of gas (bubble) diameter [m]; column AP
        # Separation
        v_E_i = (
            E / (2.0 * math.pi * b_i * s_i * rho_w) / self._dt
        )  # org. vE; entrainment velocity [m/s]; column AH
        # v_N_g_i = np.maximum(U_g_b_i * math.sin(rad(phi_i)) - v_E_i, 0.)                         # org. vNgas, normal-oriented velocity [m/s] of gas bubbles, column AI
        v_N_g_i = max(
            U_g_b_i * math.sin(rad_phi_i) - v_E_i, 0.0
        )  # org. vNgas, normal-oriented velocity [m/s] of gas bubbles, column AI
        S_g_i = (
            -2.0 * (G_g_i * v_N_g_i * self._dt) / (math.pi * b_i)
            if self._opt_sep
            else 0.0
        )  # Separation of gas [kg]; column AJ
        # v_N_o_i = np.maximum(Uzz_o_i * math.sin(rad(phi_i)) - v_E_i, 0.)                                 # org. vNoil; normal-oriented velocity [m/s] of oil droplets, column AK
        v_N_o_i = max(
            Uzz_o_i * math.sin(rad_phi_i) - v_E_i, 0.0
        )  # org. vNoil; normal-oriented velocity [m/s] of oil droplets, column AK
        S_o_i = (
            -2.0 * (G_o_i * v_N_o_i * self._dt) / (math.pi * b_i)
            if self._opt_sep
            else 0.0
        )  # Separation of oil [kg]; column AL
        # delta-Momentum
        dM_x_i = E * U_b  # momentum change dM in xy-plane [kg*m/s]; column AQ
        dM_z_i = (
            g_atm * (Q_tot_i * self._env_param.rho_w - G_tot_i) * self._dt
        )  # momentum change dM in xz-plane [kg*m/s]; column AR
        # rho_mix_i
        rho_mix_i = G_tot_i / Q_tot_i  # mixed fluid density [kg/m^3]; column T
        separated_prev = 0.0
        S_rel_g_i = 0.0

        results_data = {
            "t": [],
            "x": [],
            "z": [],
            "s": [],
            "b": [],
            "u": [],
            "w": [],
            "v": [],
            "phi": [],
            "Qgas": [],
            "Qoil": [],
            "Qwater": [],
            "Qdiss": [],
            "Qtot": [],
            "Ggas": [],
            "Goil": [],
            "Gwater": [],
            "Gdiss": [],
            "Gtot": [],
            "rom": [],
            "Mx": [],
            "Mz": [],
            "Dd": [],
            "rog": [],
            "Es": [],
            "Ef": [],
            "K": [],
            "Et": [],
            "E": [],
            "gred": [],
            "uS": [],
            "uC": [],
            "ugb": [],
            "vE": [],
            "vNgas": [],
            "Sgas": [],
            "vNoil": [],
            "Soil": [],
            "Re": [],
            "k": [],
            "dGgas": [],
            "dDb": [],
            "dMx": [],
            "dMy": [],
        }

        values = [
            t_i,
            x_i,
            z_i,
            s_i,
            b_i,
            u_i,
            w_i,
            v_i,
            phi_i,
            Q_g_i,
            Q_o_i,
            Q_w_i,
            Q_diss_i,
            Q_tot_i,
            G_g_i,
            G_o_i,
            G_w_i,
            G_diss_i,
            G_tot_i,
            rho_mix_i,
            M_x_i,
            M_z_i,
            D_g_i,
            rho_g_i,
            E_s,
            E_f,
            K,
            E_t,
            E,
            g_g_i_reduced,
            Uxx_g_i,
            U_C_g_i,
            U_g_b_i,
            v_E_i,
            v_N_g_i,
            S_g_i,
            v_N_o_i,
            S_o_i,
            Re,
            k_i,
            dG_g_i,
            dD_g_i,
            dM_x_i,
            dM_z_i,
        ]

        for key, value in zip(results_data.keys(), values):
            results_data[key].append(value)

        interval_count = 0
        if (interval_count % self._out_interval) == 0:
            sigma_i = (
                b_i / 2.0
            )  # plume radius as Gaussian std. deviation [m]; output column H
            Co_i = (
                2.0 * 1000000.0 * G_diss_i / Q_tot_i
            )  # centerline concentration of dissolved gas [ug/L]; output column I
            # compute gas balance - free gas: column O (G_g_i); dissolved: R (G_diss_i); separated = separated_prev - S_g_i; sum = G_g_0 = self._G_g_init
            # compute relative discharge of oil and gas
            P_o_i = (
                G_o_i / self._G_o_init
            )  # relative discharged oil [%] compared to overall, initially available oil; column AX = column P / column P(0)
            P_o_i *= 100.0
            P_g_i = (
                G_g_i / self._G_g_init
            )  # relative discharged gas [%] compared to overall, initially available gas; column AY = column O / column O(0)
            P_g_i *= 100.0
            P_diss_i = (
                G_diss_i / self._G_g_init
            )  # relative dissolved gas [%] compared to overall, initially available gas; column AZ = column R / column O(0)
            P_diss_i *= 100.0
            P_g_tot_i = 1.0 - (
                S_rel_g_i / self._G_g_init
            )  # relative separated gas [%] compared to overall, initially available gas; column BA = 1.0 - (column AV / column O(0))
            P_g_tot_i *= 100.0
            Pb_Pd = P_g_i + P_diss_i
            # output data - w [m/s], sigma [m]m, Co [ug/L], Poil, Pgasm Pdiss, Pb+Pd, plume rise, plume diameter
            z_rise = z_i - self.z_0
            r_i = b_i
        interval_count += 1

        output_data = {
            "N": [],
            "time": [],
            "x": [],
            "z": [],
            "v": [],
            "phi": [],
            "w": [],
            "sigma": [],
            "Co": [],
            "P_o": [],
            "P_g": [],
            "P_diss": [],
            "Pb+Pd": [],
            "plume-rise": [],
            "plume-diameter": [],
        }

        # Fill the initial variables into the dataframe
        values = [
            0,
            t_i,
            x_i,
            z_i,
            v_i,
            phi_i,
            w_i,
            sigma_i,
            Co_i,
            P_o_i,
            P_g_i,
            P_diss_i,
            Pb_Pd,
            z_rise,
            r_i,
        ]
        for key, value in zip(output_data.keys(), values):
            output_data[key].append(value)

        for i in range(1, self._N):
            t_i = t_i + self._dt
            U_b = self.U_b
            G_tot_prev = G_tot_i
            # Mass G
            G_g_i = max(G_g_i + dG_g_i + S_g_i, 0.0)
            G_o_i = G_o_i + S_o_i
            G_w_i = G_w_i + E
            G_diss_i = G_diss_i - dG_g_i
            G_tot_i = G_g_i + G_diss_i + G_o_i + G_w_i
            # Momentum
            M_x_i = M_x_i + dM_x_i
            M_z_i = M_z_i + dM_z_i
            # plume velocities
            u_i = 2.0 * M_x_i / (G_tot_prev + G_tot_i)
            w_i = 2.0 * M_z_i / (G_tot_prev + G_tot_i)
            v_i = math.sqrt((u_i**2) + (w_i**2))
            rad_phi_i = math.atan(u_i / w_i)
            phi_i = math.degrees(rad_phi_i)
            # bubble size
            D_g_i = max(D_g_i + dD_g_i, 0.0)
            # plume geometry
            x_i = x_i + u_i * self._dt
            z_i = z_i + w_i * self._dt
            s_i = v_i * self._dt
            # bubble density
            rho_g_prev = rho_g_i
            rho_g_i = self._plume_data.rho_g_0 * (
                (self._env_param.H + self._env_param.H_0 - z_i)
                / (self._env_param.H + self._env_param.H_0 - self.z_0)
            )
            # Volume Q
            Q_g_i = G_g_i / rho_g_prev
            Q_o_i = G_o_i / rho_o
            Q_w_i = G_w_i / rho_w
            Q_diss_i = G_diss_i / self._env_param.rho_g_diss
            Q_tot_i = Q_g_i + Q_diss_i + Q_o_i + Q_w_i
            # plume geometry - after Q
            b_i = math.sqrt(Q_tot_i / (math.pi * s_i))
            # Gas bubble velocity
            g_g_i_reduced = g_atm * (rho_w - rho_g_i) / rho_w
            Uxx_g_i = (
                g_g_i_reduced
                * (D_g_i * D_g_i)
                / (18.0 * self._env_param.visc_w)
            )
            U_C_g_i = math.sqrt(
                4.0 * g_g_i_reduced * D_g_i / (3.0 * self._plume_data.Cdp)
            )
            U_g_b_i = (
                1.0 / ((1.0 / Uxx_g_i) + (1.0 / U_C_g_i))
                if D_g_i > 0.0
                else 0.0
            )
            # Entrainment
            E_s = (
                2.0
                * math.pi
                * self.alpha
                * b_i
                * s_i
                * (v_i - (U_b * math.sin(rad_phi_i)))
                * rho_w
                * self._dt
            )
            E_f = (
                2.0
                * b_i
                * s_i
                * (U_b * math.cos(rad_phi_i))
                * rho_w
                * self._dt
            )
            K = self._env_param.kappa * math.sqrt(self.Cdb) * U_b * z_i
            E_t = (
                np.float64(8.0) * math.pi * K * s_i * rho_w * self._dt
                if self._opt_td
                else 0.0
            )
            E = np.max([E_s, E_f, E_t])
            # Separation
            v_E_i = E / (2.0 * math.pi * b_i * s_i * rho_w) / self._dt
            v_N_g_i = max(U_g_b_i * math.sin(rad_phi_i) - v_E_i, 0.0)
            S_g_i = (
                -2.0 * (G_g_i * v_N_g_i * self._dt) / (math.pi * b_i)
                if self._opt_sep
                else 0.0
            )
            v_N_o_i = max(Uzz_o_i * math.sin(rad_phi_i) - v_E_i, 0.0)
            S_o_i = (
                -2.0 * (G_o_i * v_N_o_i * self._dt) / (math.pi * b_i)
                if self._opt_sep
                else 0.0
            )
            # Dissolution
            Re = U_g_b_i * D_g_i / self._env_param.visc_w
            k_i = (
                self._env_param.diff_w
                * (
                    2.0
                    + 0.6
                    * math.pow(Re, 0.5)
                    * math.pow(self._env_param.schmidt_coeff, 1.0 / 3.0)
                )
                / D_g_i
                if D_g_i > 0.0
                else 0.0
            )
            dG_g_i = (
                -6.0
                * k_i
                * G_g_i
                * self._plume_data.r_sol_rho_g
                * self._dt
                / D_g_i
                if D_g_i > 0.0 and self._opt_diss
                else 0.0
            )
            dD_g_i = (D_g_i / 3.0) * (dG_g_i / G_g_i) if G_g_i > 0.0 else 0.0
            # delta-Momentum
            dM_x_i = E * U_b
            dM_z_i = g_atm * ((Q_tot_i * rho_w) - G_tot_i) * self._dt
            # rho_mix_i
            rho_mix_i = G_tot_i / Q_tot_i
            separated_prev = S_rel_g_i
            S_rel_g_i = (
                separated_prev - S_g_i
            )  # separated = separated_prev - S_g_i

            values = [
                t_i,
                x_i,
                z_i,
                s_i,
                b_i,
                u_i,
                w_i,
                v_i,
                phi_i,
                Q_g_i,
                Q_o_i,
                Q_w_i,
                Q_diss_i,
                Q_tot_i,
                G_g_i,
                G_o_i,
                G_w_i,
                G_diss_i,
                G_tot_i,
                rho_mix_i,
                M_x_i,
                M_z_i,
                D_g_i,
                rho_g_i,
                E_s,
                E_f,
                K,
                E_t,
                E,
                g_g_i_reduced,
                Uxx_g_i,
                U_C_g_i,
                U_g_b_i,
                v_E_i,
                v_N_g_i,
                S_g_i,
                v_N_o_i,
                S_o_i,
                Re,
                k_i,
                dG_g_i,
                dD_g_i,
                dM_x_i,
                dM_z_i,
            ]

            for key, value in zip(results_data.keys(), values):
                results_data[key].append(value)

            if (interval_count % self._out_interval) == 0:
                sigma_i = (
                    b_i / 2.0
                )  # plume radius as Gaussian std. deviation [m]; output column H
                Co_i = (
                    2.0 * 1000000.0 * G_diss_i / Q_tot_i
                )  # centerline concentration of dissolved gas [ug/L]; output column I
                # compute gas balance - free gas: column O (G_g_i); dissolved: R (G_diss_i); separated = separated_prev - S_g_i; sum = G_g_0 = self._G_g_init
                # compute relative discharge of oil and gas
                P_o_i = (
                    G_o_i / self._G_o_init
                )  # relative discharged oil [%] compared to overall, initially available oil; column AX = column P / column P(0)
                P_o_i *= 100.0
                P_g_i = (
                    G_g_i / self._G_g_init
                )  # relative discharged gas [%] compared to overall, initially available gas; column AY = column O / column O(0)
                P_g_i *= 100.0
                P_diss_i = (
                    G_diss_i / self._G_g_init
                )  # relative dissolved gas [%] compared to overall, initially available gas; column AZ = column R / column O(0)
                P_diss_i *= 100.0
                P_g_tot_i = 1.0 - (
                    S_rel_g_i / self._G_g_init
                )  # relative separated gas [%] compared to overall, initially available gas; column BA = 1.0 - (column AV / column O(0))
                P_g_tot_i *= 100.0
                Pb_Pd = P_g_i + P_diss_i
                # output data - w [m/s], sigma [m]m, Co [ug/L], Poil, Pgasm Pdiss, Pb+Pd, plume rise, plume diameter
                z_rise = z_i - self.z_0
                r_i = b_i
                values = [
                    i,
                    t_i,
                    x_i,
                    z_i,
                    v_i,
                    phi_i,
                    w_i,
                    sigma_i,
                    Co_i,
                    P_o_i,
                    P_g_i,
                    P_diss_i,
                    Pb_Pd,
                    z_rise,
                    r_i,
                ]
                for key, value in zip(output_data.keys(), values):
                    output_data[key].append(value)
            interval_count += 1
        output_df = pd.DataFrame(output_data)
        results_df = pd.DataFrame(results_data)
        return output_df, results_df

    def _calculate_init_sim_params_(self):
        self._tau_calc = (
            self._dt * self._plume_data.v_0 / self._plume_data.d_out
        )
        self._lambda_calc = (
            math.sqrt(2.0 * self.a_j * self._tau_calc + 1.0) - 1.0
        ) / self.a_j
        self._v_init = self._plume_data.v_0 / (
            1.0 + self.a_j * self._lambda_calc
        )
        self._G_g_init = self._plume_data.G_g_0 * self._dt
        self._G_o_init = self._plume_data.G_o_0 * self._dt
        self._G_w_init = (
            self.a_j * self._lambda_calc * (self._G_g_init + self._G_o_init)
        )


### Changing the coordinate system:
# Sensor S(x,y,z) and leakage L(xl,yl,zl) in the original coordinate system with origin at the center of template
def trans(L, S):
    x_l, y_l, z_l = L
    x, y, z = S
    X = x - x_l
    Y = y - y_l
    Z = z - z_l
    return X, Y, Z  # new coordinates of sensor S


# if we need to rotate the coordinates conterclockwise to the direction of the current
def rotate(S, phi_rot):
    x, y, z = S
    a, b = math.cos(-phi_rot), math.sin(-phi_rot)
    X = a * x - b * y
    Y = b * x + a * y
    Z = z
    return X, Y, Z  # new coordinate of the sensor


def direction_vector(a, b):
    return [b[i] - a[i] for i in range(3)]


def point_on_line(a, direction, t):
    return [a[i] + t * direction[i] for i in range(3)]


def perpendicular_direction(a, b, c):
    ab = direction_vector(a, b)

    t_num = sum(ab[i] * (c[i] - a[i]) for i in range(3))
    t_denom = sum(ab[i] * ab[i] for i in range(3))
    # The parameter t ensures that point D lies on the line with direction AB such that vector CD is perpendicular AB
    # It is calculated given the formula for projection of AC to AB (t*AB)
    t = t_num / t_denom

    d = point_on_line(a, ab, t)
    cd = direction_vector(c, d)

    return cd, d


def find_perpendicular_intersection(S, points):
    """
    S: tuple of the form (x_s, y_s, z_s) representing point S.
    points: list of (x, y, z) tuples representing points on the curve.
    Returns: tuple (x_t, 0, z_t) representing the intersection point T.
    """

    x_s, y_s, z_s = S
    min_distance = float("inf")
    closest_point = None
    indices = (None, None)

    for i in range(len(points) - 1):
        # Compute direction vector for segment
        x1, _, z1 = points[i]
        x2, _, z2 = points[i + 1]
        _, T = perpendicular_direction(points[i], points[i + 1], S)
        x_t, _, z_t = T
        # Check if the intersection point lies within the segment
        if min(x1, x2) <= x_t <= max(x1, x2) and min(z1, z2) <= z_t <= max(
            z1, z2
        ):
            # Calculate distance to the intersection point
            dist = (
                (x_s - x_t) ** 2 + (y_s - 0) ** 2 + (z_s - z_t) ** 2
            ) ** 0.5
            if dist < min_distance:
                min_distance = dist
                closest_point = (x_t, 0, z_t)
                indices = (i, i + 1)

    return closest_point, indices, min_distance


def get_concentration_sensor(
    current: Current,
    sensor: Sensor,
    leakage: Leakage,
    runtime: int,
    output_interval: int,
    verbose: bool = True,
):
    U_i, alpha_i = current.magnitude, current.angle_from_north
    S = (sensor.x, sensor.y, sensor.z)  # units m
    L = (leakage.x, leakage.y, leakage.z)
    template_angle = sensor.template.angle_from_north
    steps = runtime * 4

    _, _, z_l = L
    # change the origin to L
    S_ = copy.deepcopy(S)
    L_ = copy.deepcopy(L)
    S_ = trans(L_, S_)
    L_ = trans(L_, L_)
    # align the x coordimnate with direction of the current:
    angle = template_angle + math.pi / 2 - alpha_i
    S_ = rotate(S_, angle)

    sim = SimulationPlume2D(verbose=verbose, z_0=z_l, U_b=U_i)
    # get the results of the simulation
    df, _ = sim.run(
        runtime=runtime, steps=steps, output_interval=output_interval
    )
    # extract points from the results
    points = generate_tuples(df)
    # find the coordinate of the projection of the sensor location to the centerline
    (
        intersection_point,
        indices,
        min_distance,
    ) = find_perpendicular_intersection(S_, points)
    if intersection_point == None:
        C_i = 0.0
    else:
        Co_list = list(df["Co"])
        sigma_list = list(df["sigma"])
        i = indices[0]
        j = indices[1]
        r = min_distance

        Co = (Co_list[i] + Co_list[j]) / 2
        sigma = (sigma_list[i] + sigma_list[j]) / 2

        C_i = Co * np.exp(-(r**2) / (2 * sigma**2))

        # to transfer mg/L to ppmv. In our case we do not need to be super accurate
        C_i *= 35

    return C_i


def apply_time_constant(curve, tau=60, delta_t=10) -> NDArray[np.float64]:
    """The function to smooth the concentration values taking
    into account sensor behaviour. tau - time constant representing delay
    in the sensor response to the real signal; delta_t - the distance
    between measurements, by default for our system 10 min.
    """

    alpha = 0.5 * delta_t / tau
    sensor_curve = []
    y_n_1 = 0

    for i in range(len(curve) - 1):
        y_n = (y_n_1 * (1 - alpha) + alpha * (curve[i] + curve[i + 1])) / (
            1 + alpha
        )
        sensor_curve.append(y_n)
        y_n_1 = y_n

    return np.array(sensor_curve, dtype=np.float64)


def generate_tuples(df):
    return df.apply(
        lambda row: (row["x"], 0, row["plume-rise"]), axis=1
    ).tolist()


# Function to plot the data
def plot_sensor_data(data, signal=False):
    fig, axes = plt.subplots(nrows=len(data), figsize=(10, 15))
    for ax, (sensor, leak_data) in zip(axes, data.items()):
        for leak, y_values in leak_data.items():
            ax.plot(y_values, label=leak)
        ax.set_title(sensor)
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Concentration")
        ax.legend()
    plt.tight_layout()
    # plt.show()
    # Save the figure if a filename is provided
    if signal:
        fig.savefig(f"{settings.export_dir}/plots/results_signal.png", dpi=300)
    else:
        fig.savefig(
            f"{settings.export_dir}/plots/results_response.png", dpi=300
        )


def simulate(
    sensor: Sensor,
    anomaly_detection: AnomalyDetection,
    leakage: Leakage,
    currents: list[Current],
    runtime: int,
    tau: int,
) -> DetectionUncommited:
    # transformed_coordinates: CartesianCoordinates = (
    #    get_sensor_transformed_coordinates(sensor, leakage, current)
    # )
    tsd_id = anomaly_detection.time_series_data.id
    currents_relevant = currents[(tsd_id - 143) : (tsd_id + 1)]
    concentrations = [
        get_concentration_sensor(
            current=current,
            sensor=sensor,
            leakage=leakage,
            runtime=runtime,
            output_interval=1,
            verbose=False,
        )
        for current in currents_relevant
    ]

    concentrations_response = apply_time_constant(concentrations, tau=tau)

    # Save the image
    # plot_sensor_data(concentrations_response)

    return DetectionUncommited(
        anomaly_detection_id=anomaly_detection.id,
        leakage=leakage.dict(),
        concentrations=",".join([str(c) for c in concentrations_response]),
    )
