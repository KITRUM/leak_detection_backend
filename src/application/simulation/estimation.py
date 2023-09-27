"""
The purpose of this module is estimate the leakage by
simulation processing results.

P.S. this module is not prooved yet...
"""

import copy
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from fastdtw import fastdtw
from loguru import logger
from numpy.typing import NDArray
from scipy.signal import correlate
from scipy.spatial.distance import euclidean

from src.domain.anomaly_detection import AnomalyDeviation
from src.domain.estimation import (
    DATETIME_FORMAT,
    EstimationResult,
    EstimationSummary,
    EstimationSummaryUncommited,
)
from src.domain.fields import TagInfo
from src.domain.simulation import Detection

# TODO: Configurations should be optional and defaults are taken from configs


class MultiMetricCorrelation:
    def __init__(
        self,
        reference,
        hypotheses,
        neighbor_sensors: list[NDArray[np.float64]],
        weight_dtw=0.4,
        threshold=1.4,
        max_lag=15,
        beta=0.001,
        verbose=False,
        plot=False,
        max_lag_neighbors=6,
    ):
        """
        :param reference: the measured ppm/V signal from 'AnomalyDetector'
        :param hypotheses: array of the simulated signals from 'Simulator'
        :return:
        """

        # Parameters:
        self._x: NDArray[np.float64] = np.flip(reference)
        self._y: NDArray[np.float64] = hypotheses

        # TODO: 💩 left some shitty code
        self.neighbors = copy.deepcopy(neighbor_sensors)
        self.neighbors.append(self._x)

        self.weight_dtw = weight_dtw
        self.threshold = threshold
        self.max_lag = max_lag
        self.max_lag_neighbors = max_lag_neighbors
        self.beta = beta
        self.plot = plot
        self._verbose = verbose

        # Results crosscorrelations:
        self.crosscorr_lags = []
        self.crosscorr_values = []
        self.crosscorr_z_scores = []
        self.crosscorr_lag = 0
        self.crosscorr_mean = 0.0
        self.crosscorr_std = 0.0
        self.crosscorr_best = 0.0
        self.crosscorr_best_score = 0.0
        self.crosscorr_leak_index = None

        # Results dtw:
        self.dtw_values = []
        self.dtw_z_scores = []
        self.dtw_mean = 0.0
        self.dtw_std = 0.0
        self.dtw_best = 0.0
        self.dtw_best_score = 0.0
        self.dtw_leak_index = None

        # Neighboring sensors correlation
        self.neighbor_corrs = []
        self.neighbor_lags = []
        self.neighbor_corr_mean = 0.0

        # Main results:
        self.final_z_scores = []
        self.consensus = False
        self.extreme_indices = []

    def compute(self):
        self.run_dtw()
        self.run_crosscorr()
        self.get_consensus()
        self.run_corr_neighbors()
        if self.plot:
            self.plot_series()

    @property
    def leak_index_mat(self) -> dict:
        return {
            "crosscorr": self.crosscorr_leak_index,
            "dtw": self.dtw_leak_index,
        }

    # calculate cross correlation for all candidate leak points for a given sensor
    def run_crosscorr(self):
        """
        This function computes crosscorrelation between tsd measurements from the sensor and each simulation curve
        returns z_scores of the best correlation scores and lags of the best correlation for each leak location
        """
        reference = self._x
        for hypothesis in self._y:
            correlation = correlate(reference, hypothesis, mode="full")

            # Limit to lags within the desired range [-max_lag, max_lag]
            valid_range = len(reference) - 1  # The zero lag position
            correlation[: valid_range - self.max_lag] = 0
            correlation[valid_range + self.max_lag + 1 :] = 0

            norm_factor = np.sqrt(
                np.sum(reference**2) * np.sum(hypothesis**2)
            )

            normalized_correlation: np.float64 = (
                np.float64(0.1)
                if norm_factor < 10 ** (-6)
                else correlation / norm_factor
            )

            # Apply penalty based on lag value
            lags = np.arange(-valid_range, len(hypothesis))
            penalties = 1 + self.beta * np.abs(lags)
            penalized_correlation = normalized_correlation / penalties

            # Ensure the penalized correlation is still within the desired lag range
            penalized_correlation[: valid_range - self.max_lag] = 0
            penalized_correlation[valid_range + self.max_lag + 1 :] = 0

            lag = penalized_correlation.argmax() - valid_range
            self.crosscorr_lags.append(lag)
            self.crosscorr_values.append(penalized_correlation.max())
        self.crosscorr_mean = np.mean(self.crosscorr_values)
        self.crosscorr_std = np.std(self.crosscorr_values)

        self.crosscorr_z_scores = (
            self.crosscorr_values - self.crosscorr_mean
        ) / self.crosscorr_std
        if self._verbose:
            print(
                "Crosscorrelation: min = {}, max = {}".format(
                    np.min(self.crosscorr_values),
                    np.max(self.crosscorr_values),
                )
            )
            print(
                "Cross correlation: mean = {}, std-dev. = {}".format(
                    self.crosscorr_mean, self.crosscorr_std
                )
            )
            print(
                "Crosscorrelation Z scores: {}".format(self.crosscorr_z_scores)
            )

    def run_corr_neighbors(self):
        """
        This function computes crosscorrelation between tsd measurements from all sensors of the template and returns avarage correlation
        between them. Crosscorrelation is performed with restriction of the lags to 6 corresponding to 1 hour
        """
        if len(self.neighbors) < 2:
            return
        for i, curve_1 in enumerate(self.neighbors):
            for j, curve_2 in enumerate(self.neighbors):
                if i != j:
                    correlation = correlate(curve_1, curve_2, mode="full")

                    # Limit to lags within the desired range [-max_lag, max_lag]
                    valid_range = len(curve_1) - 1  # The zero lag position
                    correlation[: valid_range - self.max_lag_neighbors] = 0
                    correlation[valid_range + self.max_lag_neighbors + 1 :] = 0

                    norm_factor = np.sqrt(
                        np.sum(curve_1**2) * np.sum(curve_2**2)
                    )
                    normalized_correlation = correlation / norm_factor

                    lag = normalized_correlation.argmax() - valid_range
                    self.neighbor_lags.append(lag)
                    self.neighbor_corrs.append(normalized_correlation.max())
        self.neighbor_corr_mean = np.mean(self.neighbor_corrs)

        if self._verbose:
            print(
                "Neighbor correlation: min = {}, max = {}".format(
                    np.min(self.neighbor_corrs),
                    np.max(self.neighbor_corrs),
                )
            )
            print(
                "Neighbor correlation: mean = {}, std-dev. = {}".format(
                    self.neighbor_corr_mean, np.std(self.neighbor_corrs)
                )
            )

    def run_dtw(self):
        """
        This function computes dynamic time warping distances between tsd measurements from the sensor and each simulation curve
        returns z_scores of the inverse (to make it bigger - better correlation) normalized dtw for each leak location
        """
        for hypothesis in self._y:
            dtw_distance, path = fastdtw(
                np.reshape(self._x, (-1, 1)),
                np.reshape(hypothesis, (-1, 1)),
                dist=euclidean,
            )  # check dimensionality and adjust reshape()
            normalized_dtw = dtw_distance / len(path)
            self.dtw_values.append(normalized_dtw)
        self.dtw_mean = np.mean(self.dtw_values)
        self.dtw_std = np.std(self.dtw_values)

        dtw_inverse_values = 1 / np.array(self.dtw_values)
        dtw_inverse_mean = np.mean(dtw_inverse_values)
        dtw_inverse_std = np.std(dtw_inverse_values)

        self.dtw_inv_z_scores = (
            dtw_inverse_values - dtw_inverse_mean
        ) / dtw_inverse_std

        if self._verbose:
            print(
                "DTW: min = {}, max = {}".format(
                    np.min(self.dtw_values), np.max(self.dtw_values)
                )
            )
            print(
                "DTW: mean = {}, std-dev. = {}".format(
                    self.dtw_mean, self.dtw_std
                )
            )
            print(
                "Dynamic Time Warping (inversed) Z scores: {}".format(
                    self.dtw_inv_z_scores
                )
            )

    def get_consensus(self):
        # calculate weighted sum of dtw and crosscorrelation:
        self.crosscorr_leak_index = np.where(
            self.crosscorr_z_scores > self.threshold
        )[0]
        self.crosscorr_best_score = np.max(self.crosscorr_z_scores)

        self.dtw_leak_index = np.where(self.dtw_inv_z_scores > self.threshold)[
            0
        ]

        self.dtw_best_score = np.max(self.dtw_inv_z_scores)

        weighted_sum = (
            (1 - self.weight_dtw) * self.crosscorr_z_scores
            + self.weight_dtw * self.dtw_inv_z_scores
        )

        # Calculate Z-scores for weighted sum
        self.final_z_scores = (weighted_sum - np.mean(weighted_sum)) / np.std(
            weighted_sum
        )

        # Find indices with Z-scores higher than threshold
        self.extreme_indices = np.where(self.final_z_scores > self.threshold)[
            0
        ]

        # Find indices with Z-scores higher than threshold
        self.extreme_indices = np.where(self.final_z_scores > self.threshold)[
            0
        ]

        # if we have more than 1 candidate - consensus has not been reached
        if len(self.extreme_indices) == 1:
            self.consensus = True

        if self._verbose:
            print(
                f"DTW: best_score = {self.dtw_best_score},  index exceeds barrier = {self.dtw_leak_index}"
            )
            print(
                f"Crosscorrelation: best_score = {self.crosscorr_best_score},  index exceeds barrier = {self.crosscorr_leak_index}"
            )

    def plot_series(self):
        for i, series in enumerate(self._y):
            plt.figure(figsize=(10, 5))
            plt.plot(self._x, label="Reference", alpha=0.7)
            plt.plot(series, label="Leak Simulation", alpha=0.7)
            plt.title(f"Weighted Sum Score: {self.final_z_scores[i]:.2f}")
            plt.legend()
            plt.show()


class EstimationProcessor:
    """
    This class represents the main estimation services
    which includes all service's components.

    This class was created by C.Kehl so it is used without any sort of
    batteries or improvements. We just can be sure that
    this one class works as before for the spesific sensor
    """

    def __init__(
        self,
        detections: list[Detection],
        tsd_id: int,
        anomaly_severity: AnomalyDeviation,
        anomaly_concentrations: NDArray[np.float64],
        # collection of sensor signals from the rest of the sensors of the template
        neighbor_sensors: list[NDArray[np.float64]],
        anomaly_timestamps: list[str],
        sensor_number: int,
    ) -> None:
        self._detections: list[Detection] = detections
        self._concentrations: NDArray = np.array(
            [detection.concentrations for detection in self._detections]
        )

        self.nleaks = self._concentrations.shape[0]
        self.nsensors = 1  # - Weird Here we should receive the number of working sensor for current event at the current template
        self.timesteps = self._concentrations.shape[1]
        self.sensor_concentrations: NDArray = np.array(anomaly_concentrations)
        self.neighbor_sensors: list[NDArray[np.float64]] = neighbor_sensors

        timearray = [
            datetime.strptime(timestr, DATETIME_FORMAT)
            for timestr in anomaly_timestamps
        ]

        self.sensor_times: NDArray = np.array(timearray, dtype=np.datetime64)

        # ---------------------------------------------------------------
        # should be either the local id 1-4 (within a 4-sensor template),
        # or transformable into that. Used for indexing
        # self.simulator_concentrations and self.detection_rates.
        # ---------------------------------------------------------------

        self.anomaly_severity = anomaly_severity
        self.sensor_id: int = sensor_number
        # self.anomaly_severity = anomaly_severity
        self.verbose = True

    def process(self) -> EstimationSummaryUncommited:
        """This function is an entrypoint of the estimation processing."""

        print("--------        Sensor {}      --------".format(self.sensor_id))

        maxlen = min(
            len(self.sensor_concentrations),
            self._concentrations.shape[1],
        )
        reference = self.sensor_concentrations[1:maxlen]
        hypotheses = self._concentrations[:, : (maxlen - 1)]

        # TODO: Replace neighbor_sensors with real data

        # TODO:

        corr_output = MultiMetricCorrelation(
            neighbor_sensors=[],
            reference=reference,
            hypotheses=hypotheses,
            weight_dtw=0.9,
            threshold=1.4,
            max_lag=12,
            beta=0.0001,
            verbose=False,
            plot=False,
        )
        corr_output.compute()

        # NOTE:
        # *********************************************************************
        # Attributes corr_output relevant for the final results:
        # - corr_output.leak_index_mat() - method returns dictionary
        #   of leak positions according to crosscorrelation and dtw separately
        #   (value 'None' means there is no distinguishable leak)
        # - corr_output.consensus: returns True if current estimator iteration
        #   successfully found a leak location
        # - corr_output.extreme_indices: outputs the list of leak indices
        #   (sometimes it can be several, but the cosensus
        #   will be False in this case)
        # - corr_output.final_z_scores: each value: "final correlation score".
        # This score tells us how many standard deviations a particular value
        #   (specifically, the weighted sum of dynamic time warping (DTW)
        #   and cross-correlation values for a particular leak location)
        #   deviates from the mean of all such weighted sums.
        # - corr_output.neighbor_corr_mean: Mean correlation between
        # the neighboring sensors of the template. Calculated pairwise
        # with allowed lags up to 1 hour
        # *********************************************************************

        # Log some intermediate results
        logger.debug(
            f"Intermidiate correlation results: {corr_output.leak_index_mat}"
        )
        logger.debug(f"dtw distances: {corr_output.dtw_values}")
        logger.debug(f"dtw scores: {corr_output.dtw_inv_z_scores}")
        logger.debug(f"crosscorr values: {corr_output.crosscorr_values}")
        logger.debug(f"crosscorr scores: {corr_output.crosscorr_z_scores}")
        logger.debug(f"Final correlation scores: {corr_output.final_z_scores}")

        # NOTE: Currently the estimation could return next results:
        #       * Confirmed
        #       * External cause

        # TODO: Finish with other estimation summary results

        if corr_output.consensus is True:
            return EstimationSummaryUncommited(
                **{
                    "result": EstimationResult.CONFIRMED,
                    "sensor_id": self.sensor_id,
                    "detection_id": corr_output.extreme_indices[0],
                }
            )
        else:
            if corr_output.neighbor_corr_mean > 0.9:
                return EstimationSummaryUncommited(
                    **{
                        "result": EstimationResult.EXTERNAL_CAUSE,
                        "sensor_id": self.sensor_id,
                        "detection_id": None,
                    }
                )
            else:
                return EstimationSummaryUncommited(
                    **{
                        "result": EstimationResult.UNDEFINED,
                        "sensor_id": self.sensor_id,
                        "detection_id": None,
                    }
                )


def log_estimation(
    estimation_summary: EstimationSummary,
    tag_info: TagInfo,
    anomaly_timestamps: list[str],
):
    if estimation_summary.result == EstimationResult.EXTERNAL_CAUSE:
        logger.debug(
            "Detected high gas concentrations at "
            f"{anomaly_timestamps[-1]} (sensor {tag_info.sensor_number})."  # noqa
            "Concentration levels are cause by reasons "
            "other than the expected leak points."
        )
    elif estimation_summary.result == EstimationResult.CONFIRMED:
        logger.debug(
            "Detected leak for anomaly at "
            f"{anomaly_timestamps[-1]} of sensor {tag_info.sensor_number} "
            f"at leak position {estimation_summary.detection_id} "
            f"(Result: {estimation_summary.result})."
        )
    else:  # LeakResponseType.UNDEFINED
        logger.debug(
            "The methane elevation cause of the sensor "
            f"{tag_info.sensor_number} is undefined."
        )
