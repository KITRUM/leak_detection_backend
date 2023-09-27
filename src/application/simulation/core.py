"""
The purpose of this module is reflecting the general idea
of the simulation processing that producing the detections.
"""

import numpy as np
from loguru import logger

from src.application.data_lake import data_lake
from src.config import settings
from src.domain import events
from src.domain.anomaly_detection import AnomalyDetection
from src.domain.currents import Current
from src.domain.currents import services as currents_services
from src.domain.estimation import (
    DATETIME_FORMAT,
    EstimationsSummariesRepository,
    EstimationSummary,
    EstimationSummaryUncommited,
)
from src.domain.estimation.models import EstimationResult
from src.domain.fields import Field, TagInfo
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.simulation import (
    CartesianCoordinates,
    Detection,
    DetectionUncommited,
    Leakage,
    SimulationDetectionsRepository,
)
from src.domain.simulation import services as simulation_services
from src.domain.templates import TemplatesRepository
from src.domain.tsd import Tsd, TsdFlat, TsdRepository
from src.infrastructure.database import transaction_context
from src.infrastructure.errors.base import UnprocessableError
from src.infrastructure.physics import constants

from . import plume2d
from .estimation import EstimationProcessor, log_estimation

__all__ = ("process",)


def get_sensor_transformed_coordinates(
    sensor: Sensor, leak: Leakage, current: Current
) -> CartesianCoordinates:
    """Transforms the (x,y)-coordinates to fit
    into a cartesian coordinate system where:
    - The leak is at the origin in the (x,y)-plane
    - The x-axis points along the direction of the current
    """
    # Rotate the coordinates so that the x-axis points
    # along the direction of the current
    rotate_angle = (
        current.angle_from_north
        - constants.PI / 2
        - sensor.template.angle_from_north
    )
    alpha = np.cos(rotate_angle)
    beta = np.sin(rotate_angle)

    coordinates = CartesianCoordinates(
        x=np.float64(sensor.x * alpha - sensor.y * beta),
        y=np.float64(sensor.x * beta + sensor.y * alpha),
    )

    transformed_leak_x = np.float64(leak.x * alpha - leak.y * beta)
    transformed_leak_y = np.float64(leak.x * beta + leak.y * alpha)

    # Shift the coordinates so that the origin is at the leak
    coordinates.x -= transformed_leak_x
    coordinates.y -= transformed_leak_y

    return coordinates


async def process():
    """Consume fetched anomaly detection from data lake and run the simulation.
    The result is produced back to data lake and saved
    to the database for making the history available.
    WARNING: files are loaded only once for the whole processing

    WARNING: Wave and currents datasets should have the same amount of values,
             since it is required by the processing algorithm.
    """

    # NOTE: Skip if settings are set to False
    if not settings.simulation.turn_on:
        return

    if settings.debug is False:
        raise NotImplementedError(
            "Currently the simulation is not working with real data"
        )

    if settings.simulation.options.run_open_template is False:
        raise NotImplementedError(
            "Closed template simulation is not implemented yet"
        )

    leakages_dataset: list[
        Leakage
    ] = simulation_services.load_leakages_dataset(
        settings.mock_dir / "simulated_leakages.csv"
    )
    currents_dataset: list[Current] = currents_services.load_currents_dataset(
        settings.mock_dir / "environment/currents.csv"
    )

    # NOTE: Unused variable (taken from the deprecated project)
    # delta_t: np.float64 = np.float64(
    #     settings.simulation.parameters.tref / len(currents_dataset)
    # )

    # WARNING: Currently the simulation is working with only
    #          the one simulation

    logger.success("Background simulation processing")

    data_lake_items = data_lake.anomaly_detections_for_simulation
    async for anomaly_detection in data_lake_items.consume():
        # TODO: The key has to be unique for each process in order
        #       to secure parallel processing for each CRITICAL anomaly
        #       deviation received from the data lake.
        #       If you'd like to suppress the parallel execution you may
        #       use the same key for the process and handle
        #       the processes.processError which is reaised
        #       if the process is already existed.

        # NOTE: The processing is changed from multiprocessing to asyncio
        #       for the MVP, since FOR NOW we would like to send the alert
        #       if the estimation gives you the confirmation or not.
        #       We have to move back to the multiprocessing, but also
        #       it makes sense only after the notification system
        #       will be externalized. Also this operation runs only
        #       once per 10 minutes or so, so it is not a big deal
        #       to run it in the main thread as well for now.
        # processes.run(
        #     namespace="simulation",
        #     key=f"process-{anomaly_detection.id}",
        #     callback=_process,
        #     anomaly_detection=anomaly_detection,
        #     currents_dataset=currents_dataset,
        #     leakages_dataset=leakages_dataset,
        # )

        logger.success(
            f"Start processing the estimation with {anomaly_detection.id}"
        )

        async with transaction_context():
            estimation_summary: EstimationSummary = await _process(
                anomaly_detection=anomaly_detection,
                currents_dataset=currents_dataset,
                leakages_dataset=leakages_dataset,
            )
            logger.success(
                f"Estimation for {anomaly_detection.id} is done. "
                f"Estimation summary id: {estimation_summary.id}"
            )

            event: events.system.Event = await _create_event(
                estimation_summary
            )

        data_lake.events_system.storage.append(event)


async def _process(
    anomaly_detection: AnomalyDetection,
    currents_dataset: list[Current],
    leakages_dataset: list[Leakage],
) -> EstimationSummary:
    """The simulation processing entrypoint.
    This coroutine is running in the separate process.

    The last step of the processing is an estimation.
    """

    sensor: Sensor = await SensorsRepository().get(
        anomaly_detection.time_series_data.sensor_id
    )

    detections_uncommited: list[DetectionUncommited] = [
        plume2d.simulate(
            sensor=sensor,
            anomaly_detection=anomaly_detection,
            leakage=leakage,
            currents=currents_dataset,
            runtime=100,
            tau=120,
        )
        for leakage in leakages_dataset
    ]

    # Save detections to the database
    detections: list[
        Detection
    ] = await SimulationDetectionsRepository().bulk_create(
        detections_uncommited
    )

    logger.success(f"Detections created: {[d.id for d in detections]}")
    logger.debug(f"Simulation processing for {anomaly_detection.id} is done")

    # return await _perform_estimation(detections)

    # # TODO: Move to the estimation related module instead.
    # #       Encapsulate some logic to the domain layer.
    # async def _perform_estimation(
    # detections: list[Detection],
    # ) -> EstimationSummary:
    # """Perform the estimation for the given detections.
    # The result is saved to the database.
    # """

    first_detection = detections[0]

    tsd_repository = TsdRepository()
    time_series_data: Tsd = await tsd_repository.get(
        id_=first_detection.anomaly_detection.time_series_data_id
    )

    # TODO: Discuss which TSD instances should be taken from the database
    last_time_series_data: list[TsdFlat] = [
        item
        async for item in tsd_repository.filter(
            sensor_id=time_series_data.sensor.id,
            last_id=time_series_data.id,
            limit=settings.anomaly_detection.window_size,
            order_by_desc=True,
        )
    ]

    # Define the `field` for all detections
    template = await TemplatesRepository().get(
        time_series_data.sensor.template.id
    )
    field = Field.get_by_id(template.field_id)

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

    # TODO: Investigate if we do need to wait
    #       for window size elements to be populated

    # TODO: Fetch neighbor sensors concentrations from the database

    create_schema: EstimationSummaryUncommited = EstimationProcessor(
        detections=detections,
        anomaly_severity=first_detection.anomaly_detection.value,
        anomaly_concentrations=np.array(
            [tsd.ppmv for tsd in last_time_series_data]
        ),
        anomaly_timestamps=anomaly_timestamps,
        sensor_number=tag_info.sensor_number - 1,
        neighbor_sensors=[],
    ).process()

    estimation_summary = await EstimationsSummariesRepository().create(
        create_schema
    )

    log_estimation(
        estimation_summary=estimation_summary,
        tag_info=tag_info,
        anomaly_timestamps=anomaly_timestamps,
    )

    return estimation_summary


async def _create_event(
    estimation_summary: EstimationSummary,
) -> events.system.Event:
    """Just a dispatcher for the event creation."""

    match estimation_summary.result:
        case EstimationResult.CONFIRMED:
            assert (
                estimation_summary.detection_id is not None
            ), "For some reasone the detection id is None"

            detection: Detection = await SimulationDetectionsRepository().get(
                id_=estimation_summary.detection_id
            )

            return await events.system.SystemEventsRepository().create(
                schema=events.system.EventUncommited(
                    type=events.system.EventType.ALERT_CRITICAL,
                    message=(
                        "The estimation is finished. "
                        f"[{EstimationResult.CONFIRMED}]\n"
                        f"The leakage is {detection.leakage}"
                    ),
                )
            )
        case EstimationResult.EXTERNAL_CAUSE:
            assert (
                estimation_summary.detection_id is not None
            ), "For some reasone the detection id is None"

            detection = await SimulationDetectionsRepository().get(
                id_=estimation_summary.detection_id
            )
            return await events.system.SystemEventsRepository().create(
                schema=events.system.EventUncommited(
                    type=events.system.EventType.ALERT_CRITICAL,
                    message=(
                        "The estimation is finished. "
                        f"[{EstimationResult.EXTERNAL_CAUSE}]\n"
                        f"The leakage is {detection.leakage}"
                    ),
                )
            )
        case EstimationResult.UNDEFINED:
            return await events.system.SystemEventsRepository().create(
                schema=events.system.EventUncommited(
                    type=events.system.EventType.ALERT_SUCCESS,
                    message=(
                        "The estimation is finished. "
                        f"[{EstimationResult.UNDEFINED}]"
                    ),
                )
            )
        case _:
            raise UnprocessableError(message="Unknown estimation result")
