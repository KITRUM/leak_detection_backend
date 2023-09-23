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
    EstimationsSummariesRepository,
    EstimationSummary,
    EstimationSummaryUncommited,
    services,
)
from src.domain.fields import Field, TagInfo
from src.domain.simulation import Detection
from src.domain.templates import TemplatesRepository
from src.domain.tsd import Tsd, TsdFlat
from src.domain.tsd.repository import TsdRepository
from src.infrastructure.database import transaction

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
        detections: list[Detection],
        simulator_concentrations: NDArray,
        sensor_number: int,
    ) -> None:
        self._detection_rates_ids: list[int] = [rate.id for rate in detections]
        self.detection_rates: NDArray = np.array(
            [rate.concentrations for rate in detections]
        )
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


@transaction
async def process(
    detection_rates: list[Detection], field: Field | None = None
):
    tsd_repository = TsdRepository()
    first_detection_rate = detection_rates[0]

    time_series_data: Tsd = await tsd_repository.get(
        id_=first_detection_rate.anomaly_detection.time_series_data_id
    )

    last_time_series_data: list[TsdFlat] = [
        item
        async for item in tsd_repository.filter(
            sensor_id=time_series_data.sensor.id,
            last_id=time_series_data.id,
            limit=settings.anomaly_detection.window_size,
            order_by_desc=True,
        )
    ]

    if field is None:
        # Define the field for all detections
        template = await TemplatesRepository().get(
            time_series_data.sensor.template.id
        )
        field = Field.get_by_id(template.id)

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

    tag_info: TagInfo = field.value.sensor_keys_callback(
        time_series_data.sensor.name.replace(field.value.tag, "")
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
        detections=detection_rates,
        simulator_concentrations=np.array(
            [detection.concentrations for detection in detection_rates]
        ),
        sensor_number=tag_info.sensor_number - 1,
    )

    estimation_summary_uncommited: EstimationSummaryUncommited = (
        estimation_processor.process()
    )

    estimation_summary: EstimationSummary = (
        await EstimationsSummariesRepository().create(
            estimation_summary_uncommited
        )
    )
    # Update the data lake for websocket connections
    data_lake.estimation_summary_set_by_sensor[
        estimation_summary.sensor_id
    ].storage.append(estimation_summary)

    log_estimation(
        estimation_summary=estimation_summary,
        tag_info=tag_info,
        anomaly_timestamps=anomaly_timestamps,
    )
