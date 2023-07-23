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
    services,
)
from src.domain.platforms import Platform, TagInfo
from src.domain.templates import services as templates_services
from src.domain.tsd import Tsd, TsdInDb
from src.domain.tsd import services as tsd_services
from src.infrastructure.errors.base import BaseError

__all__ = ("process",)


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
        anomaly_severity: AnomalyDeviation,
        anomaly_concentrations: NDArray[np.float64],
        anomaly_timestamps: list[str],
        detection_rates: NDArray[np.float64],
        simulator_concentrations: NDArray,
        sensor_number: int,
    ) -> None:
        self.detection_rates: NDArray = detection_rates
        self.simulator_concentrations: NDArray = simulator_concentrations

        assert (
            self.detection_rates.shape[0]
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
        self.nsensors = 1
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
        self.anomaly_severity = anomaly_severity
        self.verbose = True

    def process(self):
        """This function is an entrypoint of the estimation processing."""
        # =============================================================
        # TODO: Add the estimation processing functionality
        # =============================================================

        result = EstimationSummary(
            result=EstimationResult.SENSOR_NOT_AVAILABLE,
            confidence=np.float64(0.0),
            leakage_index=-1,
        )
        corrmat = {"mi": 0, "dtw": 0, "mpdist": 0}
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

        corr1 = services.MultiMetricCorrelation(
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
            result = EstimationSummary(
                result=EstimationResult.CONFIRMED,
                confidence=np.float64(Q),
                leakage_index=leak_index,
            )
        else:
            if self.anomaly_severity == AnomalyDeviation.CRITICAL:
                result = EstimationSummary(
                    result=EstimationResult.EXTERNAL_CAUSE,
                    confidence=np.float64(1.0),
                    leakage_index=-1,
                )
            else:
                result = EstimationSummary(
                    result=EstimationResult.ABSENT,
                    confidence=np.float64(
                        np.float64(1.0)
                        - np.float64(corr1.range_check())  # type: ignore
                    ),
                    leakage_index=-1,
                )

        return result


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

    # -------------------------------------------------------------------------
    # Consume and process simulations for the estimation
    # -------------------------------------------------------------------------
    async for detection_rates in simulation_detection_rates.consume():
        try:
            # If there is no detection_rates in consumed instance just skip this one
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
            TsdInDb
        ] = await tsd_services.get_last_tsd_set(
            sensor_id=time_series_data.sensor.id, id_=time_series_data.id
        )

        if platform is None:
            # Define the platform for all detections
            template = await templates_services.get_template_by_id(
                time_series_data.sensor.template_id,
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
        # TODO: investigate if we do need to wait for window size elements to be populated
        estimation_processor = DeprecatedEstimationProcessor(
            anomaly_severity=first_detection_rate.anomaly_detection.value,
            anomaly_concentrations=np.array(
                [tsd.ppmv for tsd in last_time_series_data]
            ),
            anomaly_timestamps=anomaly_timestamps,
            detection_rates=np.array(
                [detection.rate for detection in detection_rates],
                dtype=np.float64,
            ),
            simulator_concentrations=np.array(
                [detection.concentrations for detection in detection_rates]
            ),
            sensor_number=tag_info.sensor_number - 1,
        )

        try:
            # NOTE: Currently we do not care about this processor that much,
            #       so all errors are handled
            leak_estimation_result: EstimationSummary = (
                estimation_processor.process()
            )
        except BaseError as error:
            logger.error(error)
            continue

        # Define the event type and log message
        # base on the estimation result
        if leak_estimation_result.result == EstimationResult.EXTERNAL_CAUSE:
            logmsg = (
                "Detected high gas concentrations at "
                f"{anomaly_timestamps[-1]} (sensor {tag_info.sensor_number})."  # noqa
                "Concentration levels are cause by reasons "
                "other than the expected leak points."
            )
        elif leak_estimation_result.result == EstimationResult.CONFIRMED:
            logmsg = (
                "Detected leak for anomaly at "
                f"{anomaly_timestamps[-1]} of sensor {tag_info.sensor_number} "  # noqa
                f"at leak position {leak_estimation_result.leakage_index} "  # noqa
                f"(confidence: {leak_estimation_result.confidence})."
            )
        else:  # LeakResponseType.LEAK_ABSENT
            logmsg = (
                "Elevated gas levels at sensor "
                f"{tag_info.sensor_number} are not crucial."  # noqa
            )

        logger.debug(logmsg)
