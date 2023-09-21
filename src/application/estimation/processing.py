from loguru import logger

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.estimation import EstimationResult, EstimationSummary
from src.domain.fields import TagInfo
from src.domain.simulation import Detection

from . import core

__all__ = ("process",)


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

    if settings.debug is False:
        raise NotImplementedError(
            "Currently the simulation is not working with real data"
        )

    logger.success("Background estimation processing")

    # -------------------------------------------------------------------------
    # Consume and process simulation detections by the estimation module
    # -------------------------------------------------------------------------
    async for detections in data_lake.simulation_detections.consume():
        try:
            first_detection: Detection = detections[0]
            logger.debug(
                "[Estimation] "
                f"Anomaly detection id: {first_detection.anomaly_detection.id}"
            )
        except IndexError:
            logger.error("Estimation got an empty list of detections...")
            continue

        try:
            # NOTE: Currently only the latest approach is used
            estimation_summary: EstimationSummary = await core.process(
                detections=detections
            )
            logger.success(estimation_summary)
        except IndexError:
            # If there is no detection_rates in consumed instance
            # just skip this one
            logger.error(
                "Simulation consumed instance does have have any items"
            )
            continue
        except Exception as error:
            # NOTE: Currently we do not care about this processor that much,
            #       so all errors are handled
            logger.error(error)
            continue

        # TODO: Update the data lake consuming logic
        # # Update the data lake for websocket connections
        # data_lake.estimation_summary_set_by_sensor[1].storage.append(
        #     estimation_summary
        # )
