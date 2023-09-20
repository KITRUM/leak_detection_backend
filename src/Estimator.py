
"""
The purpose of this module is estimate the leakage by
simulation processing results.

P.S. this module is not proofed yet...
"""

from datetime import datetime

import numpy as np
from loguru import logger
from numpy.typing import NDArray

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.anomaly_detection import AnomalyDeviation
from src.domain.estimation import (
    DATETIME_FORMAT,
    EstimationResult,
    EstimationSummary,
    EstimationSummaryUncommited,
    services,
)
from src.domain.platforms import Platform, TagInfo
from src.domain.simulation import Detection
from src.domain.templates import services as templates_services
from src.domain.tsd import Tsd, TsdFlat
from src.domain.tsd import services as tsd_services

import pandas as pd
import copy
import random
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
import pickle
from datetime import datetime, timedelta


class MultiMetricCorrelation(object):

    def __init__(
        self, reference, hypotheses, weight_dtw = 0.5, threshold = 1.645, max_lag=20, beta=0.002, verbose=False, plot=False
    ):
        """
        :param reference: the measured ppm/V signal from 'AnomalyDetector'
        :param hypotheses: array of the simulated signals from 'Simulator'
        :return:
        """
        self._x = reference
        self._y = hypotheses
        self.weight_dtw = weight_dtw
        self.threshold = threshold
        self.max_lag = max_lag 
        self.beta = beta

        self.crosscorr_lags = []
        self.crosscorr_values = []
        self.crosscorr_z_scores = []
        self.crosscorr_lag  = 0
        self.crosscorr_mean = 0.0
        self.crosscorr_std = 0.0
        self.crosscorr_best = 0.0
        self.crosscorr_best_score = 0.0
        self.crosscorr_leak_index = None

        self.dtw_values = []
        self.dtw_z_scores = []
        self.dtw_mean = 0.0
        self.dtw_std = 0.0
        self.dtw_best = 0.0
        self.dtw_best_score = 0.0
        self.dtw_leak_index = None

        self.final_z_scores = []
        self.consensus = True
        self.extreme_indices = []
        self._verbose = verbose
        self._plot = plot

    def compute(self):
        self.run_dtw()
        self.run_crosscorr()
        self.get_consensus()
        if self._plot:
            self.plot_series()

    @property
    def leak_index_mat(self) -> dict:
        return {
            "crosscorr": self._crosscorr_index,
            "dtw": self._dtw_index,
        }
    #calculate cross correlation for all candidate leak points for a given sensor
    def run_crosscorr(self):
        '''
        This function computes crosscorrelation between tsd measurements from the sensor and each simulation curve 
        returns z_scores of the best correlation scores and lags of the best correlation for each leak location
        '''
        reference = self._x
        for hypothesis in self._y:
            correlation = correlate(reference, hypothesis, mode="full")
            
            # Limit to lags within the desired range [-max_lag, max_lag]
            valid_range = len(reference) - 1  # The zero lag position
            correlation[:valid_range - self.max_lag] = 0
            correlation[valid_range + self.max_lag + 1:] = 0
            
            norm_factor = np.sqrt(np.sum(reference**2) * np.sum(hypothesis**2))
            normalized_correlation = correlation / norm_factor
            
            # Apply penalty based on lag value
            lags = np.arange(-valid_range, len(hypothesis))
            penalties = 1 + self.beta * np.abs(lags)
            penalized_correlation = normalized_correlation / penalties
            
            # Ensure the penalized correlation is still within the desired lag range
            penalized_correlation[:valid_range - self.max_lag] = 0
            penalized_correlation[valid_range + self.max_lag + 1:] = 0
            
            lag = penalized_correlation.argmax() - valid_range
            self.crosscorr_lags.append(lag)
            self.crosscorr_values.append(penalized_correlation.max())
        self.crosscorr_mean = np.mean(self.crosscorr_values)
        self.crosscorr_std = np.std(self.crosscorr_values)

        self.crosscorr_z_scores = (self.crosscorr_values - self.crosscorr_mean)/self.crosscorr_std
        if self._verbose:
            print(
                "Crosscorrelation - min = {}, max = {}".format(np.min(self.crosscorr_values), np.max(self.crosscorr_values)
                )
            )
            print(
                "DTW - mean = {}, std-dev. = {}".format(
                    self.crosscorr_mean, self.crosscorr_std
                )
            )
            print("Crosscorrelation Z scores: {}".format(self.crosscorr_z_scores))
    
    def run_dtw(self):
        '''
        This function computes dynamic time warping distances between tsd measurements from the sensor and each simulation curve 
        returns z_scores of the inverse (to make it bigger - better correlation) normalized dtw for each leak location
        '''

        for hypothesis in self._y:
            dtw_distance, path = fastdtw(np.reshape(self._x, (-1, 1)), np.reshape(hypothesis, (-1, 1)), dist=euclidean)#check dimensionality and adjust reshape()
            normalized_dtw = dtw_distance / len(path)
            self.dtw_values.append(normalized_dtw)
        self.dtw_mean = np.mean(self.dtw_values)
        self.dtw_std = np.std(self.dtw_values)
        
        dtw_inverse_values = 1/ self.crosscorr_values
        dtw_inverse_mean = np.mean(dtw_inverse_values)
        dtw_inverse_std = np.std(dtw_inverse_values)
        
        self.dtw_inv_z_scores = (dtw_inverse_values - dtw_inverse_mean)/dtw_inverse_std 

        if self._verbose:
            print(
                "DTW - min = {}, max = {}".format(np.min(self.dtw_values), np.max(self.dtw_values)
                )
            )
            print(
                "DTW - mean = {}, std-dev. = {}".format(
                    self._dtw_mean, self._dtw_sigma
                )
            )
            print("Dynamic Time Warping (inversed) Z scores: {}".format(self.dtw_inv_z_scores))

    def get_consensus(self):
        #calculate weighted sum of dtw and crosscorrelation:
        self.crosscorr_leak_index = np.where(self.crosscorr_z_scores > self.threshold)[0]
        self.crosscorr_best_score = np.max(self.crosscorr_z_scores)

        self.dtw_leak_index = np.where(self.dtw_inv_z_scores > self.threshold)[0]
        self.dtw_best_score = np.max(self.dtw_inv_z_scores)

        weighted_sum = (1 - self.weight_dtw)*self.crosscorr_z_scores + self.weight_dtw * self.dtw_inv_z_scores

        # Calculate Z-scores for weighted sum
        self.final_z_scores = (weighted_sum - np.mean(weighted_sum)) / np.std(weighted_sum)

        # Find indices with Z-scores higher than threshold
        self.extreme_indices = np.where(self.final_z_scores > self.threshold)[0]
        
        # Find indices with Z-scores higher than threshold
        self.extreme_indices = np.where(self.final_z_scores > self.threshold)[0]
        
        #if we have more than 1 candidate - consensus has not been reached
        if self.extreme_indices != 1:
            self.consensus = False
        
        if self._verbose:
            print(f"DTW - best_score = {self.dtw_best_score},  index exceeds barrier = {self.dtw_leak_index}")
            print(f"Crosscorrelation - best_score = {self.crosscorr_best_score},  index exceeds barrier = {self.crosscorr_leak_index}")
    
    def plot_series(self):

        for i, series in enumerate(self._y) :
            plt.figure(figsize=(10, 5))
            plt.plot(self._x, label="Reference", alpha=0.7)
            plt.plot(series, label="Leak Simulation", alpha=0.7)
            plt.title(f"Weighted Sum Score: {self.final_z_scores[i]:.2f}")
            plt.legend()
            plt.show()



class DeprecatedEstimationProcessor:
    """
    This class represents the main estimation services
    which includes all service's components.

    This class was created by C.Kehl so it is used without any sort of
    batteries or improvements. We just can be sure that
    this one class works as before for the spesific sensor
    """

    def __init__(
        self,
        #anomaly_severity: AnomalyDeviation,
        anomaly_concentrations: NDArray[np.float64],
        anomaly_timestamps: list[str],
        detections: list[Detection],
        simulator_concentrations: NDArray,
        sensor_number: int,
    ) -> None:
        self._detection_rates_ids: list[int] = [
            rate.id for rate in detection_rates
        ]
        self.detection_rates: NDArray = np.array(
            [rate.concentrations for rate in detection_rates]
        )
        self.simulator_concentrations: NDArray = simulator_concentrations

        assert (
            self.detections.shape[0]
            == self.simulator_concentrations.shape[0]
        ) 
        # =============================================== #
        # Comment C.Kehl: remember that 'detection_rates' #
        # has one more entry of 'sensor_i' (dim 1) than   #
        # 'simulator_concentrations'. That one more entry #
        # is the entry of the 'average detection rate of  #
        # all sensors for that leak'. Hence:              #
        # self.detection_rates.shape[1] =                 #
        # self.simulator_concentrations.shape[1] + 1      #
        # =============================================== #

        self.nleaks = self.simulator_concentrations.shape[0]
        self.nsensors = 1 #- Weird Here we should receive the number of working sensor for current event at the current template
        self.timesteps = self.simulator_concentrations.shape[1]
        self.sensor_concentrations: NDArray = np.array(anomaly_concentrations)

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

        self.sensor_id: int = sensor_number
        #self.anomaly_severity = anomaly_severity
        self.verbose = True

    def process(self):
        """This function is an entrypoint of the estimation processing."""
        # =============================================================
        # TODO: Add the estimation processing functionality
        # =============================================================

        #corrmat = {"croscor": 0, "dtw": 0}
        # Leak correlation matrix: nr_sensors x nr_leaks
        leak_mat = np.zeros((self.nsensors, self.nleaks), dtype=np.int32)
        result_tracker = None
        print("--------        Sensor {}      --------".format(self.sensor_id))

        maxlen = min(
            len(self.sensor_concentrations),
            self.simulator_concentrations.shape[1],
        )
        reference = self.sensor_concentrations[:maxlen]
        N = self.simulator_concentrations.shape[1]
        hypotheses = np.squeeze(self.simulator_concentrations[:, N - maxlen :])

        corr1 = services.correlation.MultiMetricCorrelation(
            reference=reference,
            hypotheses=hypotheses,
            verbose=self.verbose,
        )
        corr1.compute()
        result_tracker = (
            corr1.all_exceed_sigma_squared(),
            ("mi", "dtw", "mpdist"),
        )

        print("All metrics exceed sigma-squared ? {}".format(result_tracker))

        if not result_tracker[0]:
            result_tracker = corr1.consensus_exceed_sigma_squared()
            print(
                "Consensus metrics exceed sigma-squared ? {} ({})".format(
                    result_tracker[0], result_tracker[1]
                )
            )
        if result_tracker[0]:
            leak_index = corr1.consensus_index()
            q1 = corr1.consensus_quality()
            q2 = self.detection_rates[leak_index]
            Q = q1 * q2
            print("q1: {}; q2: {}; Q: {}".format(q1, q2, Q))
            local_leak_mat = corr1.leak_index_mat
            for method_id in result_tracker[1]:
                corrmat[method_id] += 1
                leak_mat[0, local_leak_mat[method_id]] += 1
            return EstimationSummaryUncommited(
                **{
                    "result": EstimationResult.CONFIRMED,
                    "confidence": float(Q),
                    "leakage_index": leak_index,
                    "simulation_detection_rate_ids": self._detection_rates_ids,
                    "sensor_id": self.sensor_id,
                }
            )
        else:
            if self.anomaly_severity == AnomalyDeviation.CRITICAL:
                return EstimationSummaryUncommited(
                    **{
                        "result": EstimationResult.EXTERNAL_CAUSE,
                        "confidence": 1.0,
                        "leakage_index": -1,
                        "simulation_detection_rate_ids": (
                            self._detection_rates_ids
                        ),
                        "sensor_id": self.sensor_id,
                    }
                )
            else:
                return EstimationSummaryUncommited(
                    **{
                        "result": EstimationResult.ABSENT,
                        "confidence": float(
                            np.float64(1.0)
                            - np.float64(corr1.range_check())  # type: ignore
                        ),
                        "leakage_index": -1,
                        "simulation_detection_rate_ids": (
                            self._detection_rates_ids
                        ),
                        "sensor_id": self.sensor_id,
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
            f"{anomaly_timestamps[-1]} of sensor {tag_info.sensor_number} "  # noqa
            f"at leak position {estimation_summary.leakage_index} "  # noqa
            f"(confidence: {estimation_summary.confidence})."
        )
    else:  # LeakResponseType.LEAK_ABSENT
        logger.debug(
            "Elevated gas levels at sensor "
            f"{tag_info.sensor_number} are not crucial."  # noqa
        )


async def process():
    """Consume simulation detection rates from data lake
    and run the estimation. The results are saved to the database
    and data lake for consuming by websockets.
    """

    # If the simulation is turned off there is no reason to proceed
    if not settings.simulation.turn_on:
        return
    
    #get the anomaly status
    #if anomaly_detection status is Critical:
    #    remember the date
    # NOTE: Since, we do not wanna abuse the database it is better to add the
    #       platform enclosed variable for all items in the loop
    platform: Platform | None = None






    simulation_detection_rates = data_lake.simulation_detection_rates  # alias



async def process():
    """Consume simulation detection rates from data lake
    and run the estimation. The results are saved to the database
    and data lake for consuming by websockets.
    """

    # If the simulation is turned off there is no reason to proceed
    if not settings.simulation.turn_on:
        return

    if settings.debug is False:
        raise NotImplementedError(
            "Currently the simulation is not working with real data"
        )

    # NOTE: Since, we do not wanna abuse the database it is better to add the
    #       platform enclosed variable for all items in the loop
    platform: Platform | None = None

    simulation_detection_rates = data_lake.simulation_detection_rates  # alias

    logger.success("Background estimation processing")

    # -------------------------------------------------------------------------
    # Consume and process simulations for the estimation
    # -------------------------------------------------------------------------
    async for detection_rates in simulation_detection_rates.consume():
        logger.debug(f"Estimation processing for {detection_rates}")

        try:
            # If there is no detection_rates in consumed instance
            # just skip this one
            first_detection_rate = detection_rates[0]
        except IndexError:
            logger.error(
                "Simulation consumed instance does have have any items"
            )
            continue

        time_series_data: Tsd = await tsd_services.get_by_id(
            id_=first_detection_rate.anomaly_detection.time_series_data_id
        )

        last_time_series_data: list[
            TsdFlat
        ] = await tsd_services.get_last_window_size_set(
            sensor_id=time_series_data.sensor.id, last_id=time_series_data.id
        )

        if platform is None:
            # Define the platform for all detections
            template = await templates_services.get_template_by_id(
                time_series_data.sensor.template.id,
            )
            platform = Platform.get_by_id(template.id)

        # NOTE: regarding `tag_info`
        # ========================================== #
        # Comment C.Kehl: for now, this ONLY works   #
        # if the sensors in the frontend are added   #
        # (in terms of their tag) from the beginning #
        # (i.e. from the sensor of a template with   #
        # sensor number '1') in sequence to the last #
        # sensor (i.e. sensor number '4').           #
        #                                            #
        # For an arbitrary insertion order, this     #
        # procedure needs to map the sensor number   #
        # to the correct index (from the insertion   #
        # order) within the 'SensorsRepository()'    #
        # sensor list.                               #
        # ========================================== #

        tag_info: TagInfo = platform.value.sensor_keys_callback(
            time_series_data.sensor.name.replace(platform.value.tag, "")
        )

        anomaly_timestamps: list[str] = [
            tsd.timestamp.strftime(DATETIME_FORMAT)
            for tsd in last_time_series_data
        ]
        # TODO: investigate if we do need to wait
        #       for window size elements to be populated
        estimation_processor = DeprecatedEstimationProcessor(
            anomaly_severity=first_detection_rate.anomaly_detection.value,
            anomaly_concentrations=np.array(
                [tsd.ppmv for tsd in last_time_series_data]
            ),
            anomaly_timestamps=anomaly_timestamps,
            detection_rates=detection_rates,
            simulator_concentrations=np.array(
                [detection.concentrations for detection in detection_rates]
            ),
            sensor_number=tag_info.sensor_number - 1,
        )

        try:
            # NOTE: Currently we do not care about this processor that much,
            #       so all errors are handled
            estimation_summary_uncommited: EstimationSummaryUncommited = (
                estimation_processor.process()
            )
        except Exception as error:
            logger.error(error)
            continue

        estimation_summary: EstimationSummary = await services.save(
            estimation_summary_uncommited
        )

        # Update the data lake for websocket connections
        data_lake.estimation_summary_set_by_sensor[
            time_series_data.sensor.id
        ].storage.append(estimation_summary)

        log_estimation(
            estimation_summary=estimation_summary,
            tag_info=tag_info,
            anomaly_timestamps=anomaly_timestamps,
        )
