import matplotlib.pyplot as plt
import numpy as np
from fastdtw import fastdtw
from numpy.typing import NDArray
from scipy.signal import correlate
from scipy.spatial.distance import euclidean

__all__ = ("MultiMetricCorrelation",)


class MultiMetricCorrelation(object):
    def __init__(
        self,
        reference,
        hypotheses,
        weight_dtw=0.4,
        threshold=1.645,
        max_lag=20,
        beta=0.002,
        verbose=False,
        plot=False,
    ):
        """
        :param reference: the measured ppm/V signal from 'AnomalyDetector'
        :param hypotheses: array of the simulated signals from 'Simulator'
        :return:
        """
        # Parameters:
        self._x = reference
        self._y = hypotheses
        self.weight_dtw = weight_dtw
        self.threshold = threshold
        self.max_lag = max_lag
        self.beta = beta
        self.plot = plot

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

        # Main results:
        self.final_z_scores = []
        self.consensus = False
        self.extreme_indices = []
        self._verbose = verbose

    def compute(self):
        self.run_dtw()
        self.run_crosscorr()
        self.get_consensus()
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
            normalized_correlation = correlation / norm_factor

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
                "DTW: mean = {}, std-dev. = {}".format(
                    self.crosscorr_mean, self.crosscorr_std
                )
            )
            print(
                "Crosscorrelation Z scores: {}".format(self.crosscorr_z_scores)
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

        dtw_inverse_values: NDArray[np.float64] = 1 / np.array(
            self.crosscorr_values
        )
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
                    self.dtw_mean, self.dtw_sigma
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
