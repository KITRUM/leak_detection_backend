"""
This module includes all high-level sensors operations.

⚠️ Every `settings.sensors.anomaly_detection.baseline_selection_interval`
the background task goes to the baselines bank which placed in the seed/ fodler
and start the selection of the BEST baseline for this range of TSD items.

⚠️ Every `settings.sensors.anomaly_detection.baseline_best_selection_interval`
the background task goes to the baselines bank which placed in the seed/ fodler
and start the selection of the BEST baseline for this range of TSD items.

⚡️ The selection and update tasks are CPU-bound,
so they run in a separate processes.

The purpose of this package is extending the anomaly detection
feature with background initial baselines selection and update.

This package includes baselines-related components:
    1. ✨ sensor select best baseline background feature
    2. ✨ sensor initial baseline update background feature
"""


import asyncio
import pickle
from collections import defaultdict
from contextlib import suppress
from time import sleep
from typing import Any, AsyncGenerator, Coroutine

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from stumpy import aampi

from src.application.data_lake import data_lake
from src.config import settings
from src.domain.anomaly_detection import SeedBaseline
from src.domain.anomaly_detection import services as services
from src.domain.events import system
from src.domain.events.system.repository import SystemEventsRepository
from src.domain.sensors import (
    Sensor,
    SensorBase,
    SensorConfigurationUncommited,
    SensorConfigurationUpdatePartialSchema,
    SensorCreateSchema,
    SensorsConfigurationsRepository,
    SensorsRepository,
    SensorUncommited,
)
from src.domain.sensors.models import (
    SensorConfigurationFlat,
    SensorUpdatePartialSchema,
)
from src.domain.tsd import TsdFlat
from src.domain.tsd.repository import TsdRepository
from src.infrastructure.database import transaction
from src.infrastructure.errors import NotFoundError, UnprocessableError

# NOTE: Once the selected baseline is updated with consumed TSD instances
#       this list is used as a temporary storage
# Structure:
# {
#     "sensor_id": {
#         "selected_baseline_filename": aampi_object
#     }
# }
UPDATED_BASELINES_BY_SENSOR: dict[int, dict[str, aampi]] = defaultdict(dict)
WINDOW_SIZE: int = settings.anomaly_detection.window_size


# ************************************************
# ********** CRUD operations **********
# ************************************************
@transaction
async def by_template(template_id: int) -> list[Sensor]:
    """Get all sensors by template id."""

    return [
        instance
        async for instance in SensorsRepository().by_template(template_id)
    ]


@transaction
async def by_pinned(value: bool) -> list[Sensor]:
    """Get all sensors by pinned state."""

    return [
        instance async for instance in SensorsRepository().filter(pinned=value)
    ]


@transaction
async def retrieve(sensor_id: int) -> Sensor:
    """Retrieve the sensor by id."""

    return await SensorsRepository().get(id_=sensor_id)


@transaction
async def update(
    sensor_id: int,
    schema: SensorUpdatePartialSchema = (SensorUpdatePartialSchema()),
) -> Sensor:
    """Update the sensor and the configuration in one transaction hop."""

    # PERF: Abusing the database. (not critical for now)

    sensor_repository = SensorsRepository()

    # TODO: Replace with .exists() method
    sensor: Sensor = await sensor_repository.get(id_=sensor_id)

    # Update the sensor's payload if defined
    with suppress(UnprocessableError):
        await sensor_repository.update_partially(id_=sensor.id, schema=schema)

    return await sensor_repository.get(id_=sensor_id)


@transaction
async def create(template_id: int, sensor_payload: SensorBase) -> Sensor:
    """This function takes care about the sensor creation.
    The sensor creation consist of:
        1. creating the default sensor's configuration
            1.1. the initial baseline from seed files
                 is added to the configuration
        2. creating the sensor and attaching the configuration to it
    """

    anomaly_detection_initial_baseline: aampi = (
        services.baselines.seed.by_level(level="high")
    )

    initial_baseline_flat: bytes = pickle.dumps(
        anomaly_detection_initial_baseline
    )

    create_schema = SensorCreateSchema(
        configuration_uncommited=SensorConfigurationUncommited(
            interactive_feedback_mode=False,
            anomaly_detection_initial_baseline_raw=initial_baseline_flat,
        ),
        template_id=template_id,
        sensor_payload=sensor_payload,
    )

    sensors_repository = SensorsRepository()
    configurations_repository = SensorsConfigurationsRepository()

    configuration: SensorConfigurationFlat = (
        await configurations_repository.create(
            create_schema.configuration_uncommited
        )
    )

    _sensor_uncommited_payload: dict[
        str, Any
    ] = create_schema.sensor_payload.dict() | {
        "template_id": create_schema.template_id,
        "configuration_id": configuration.id,
    }
    sensor: Sensor = await sensors_repository.create(
        SensorUncommited(**_sensor_uncommited_payload)
    )

    return sensor


@transaction
async def delete(sensor_id: int) -> None:
    """This function takes care about the sensor deletion.
    The sensor deletion consist of:
        1. deleting the sensor's configuration
        2. deleting the sensor
    """

    configuration_repository = SensorsConfigurationsRepository()
    sensors_repository = SensorsRepository()
    sensor: Sensor = await sensors_repository.get(id_=sensor_id)

    tasks: list[Coroutine] = [
        configuration_repository.delete(id_=sensor.configuration.id),
        sensors_repository.delete(id_=sensor_id),
    ]

    await asyncio.gather(*tasks)


@transaction
async def toggle_interactive_feedback_mode(sensor_id: int) -> Sensor:
    """This function takes care about the sensor's
    interactive feedback mode toggling.

    Toggle feature is available only if the sensor has enough
    time series data to calculate the baseline.
    """

    sensor_repository = SensorsRepository()
    tsd_amount: int = await sensor_repository.tsd_count(sensor_id=sensor_id)

    if tsd_amount < WINDOW_SIZE:
        raise UnprocessableError(
            message=(
                "The interactive feedback mode is not available "
                "until the first time series data is collected."
                f"\nCurrent amount of time series data: {tsd_amount}"
            )
        )

    sensor: Sensor = await sensor_repository.get(id_=sensor_id)

    await SensorsConfigurationsRepository().update_partially(
        id_=sensor.configuration.id,
        schema=SensorConfigurationUpdatePartialSchema(
            interactive_feedback_mode=(
                # Reverse the current state
                not sensor.configuration.interactive_feedback_mode
            )
        ),
    )

    # Return the rich data model
    return await sensor_repository.get(id_=sensor_id)


@transaction
async def toggle_pin(sensor_id: int) -> Sensor:
    """This function takes care about the sensor's pin state toggling."""

    sensor_repository = SensorsRepository()
    sensor: Sensor = await sensor_repository.get(id_=sensor_id)

    await SensorsConfigurationsRepository().update_partially(
        id_=sensor.configuration.id,
        schema=SensorConfigurationUpdatePartialSchema(
            pinned=(
                # Reverse the current state
                not sensor.configuration.pinned
            )
        ),
    )

    # Return the rich data model
    return await sensor_repository.get(id_=sensor_id)


async def create_system_event(schema: system.EventUncommited) -> system.Event:
    """This function takes care about the system event creation."""

    event: system.Event = await system.SystemEventsRepository().create(schema)
    data_lake.events_system.storage.append(event)

    return event


# ************************************************
# ********** Backgorund processes  **********
# ************************************************
def select_best_baseline():
    """This function runs the baseline selection process.

    🚩 The flow:
    1. take all historical data starting from the last baseline selection.
        if the first baseline selection - get all records.
    2. clean concentrations.
    3. Iterate through each baseline from the seed bank
        and update with cleaned concentrations.

    P.S. The process starts every ~15 days.

    ⚠️  The process runs every N seconds where N is usually ~15 days
    since the selection process is quite complicated from the
    competition perspective.
    """

    while True:
        # Defines the break for collecting enough data
        sleep(
            settings.sensors.anomaly_detection.baseline_best_selection_interval.total_seconds()  # noqa: E501
        )
        asyncio.run(_select_best_baseline())
        # await _select_best_baseline()


@transaction
async def _select_best_baseline():
    # WARNING: Other pre-feature validations are not added

    seed_baselines: list[
        SeedBaseline
    ] = services.baselines.seed.for_select_best()

    # Select the best baseline for each sensor and update it in the database
    # if seed baseline feets the needs
    async for sensor in SensorsRepository().filter():
        logger.info(f"Best baseline seelction for {sensor.name}...")
        ERROR_MESSAGE_TSD_NOT_FOUND = (
            "The initial baseline selection is possible "
            "only in case time series data exists in the database. "
            f"Sensor: {sensor.name}"
        )

        try:
            tsd_set: AsyncGenerator[TsdFlat, None] = TsdRepository().filter(
                sensor_id=sensor.id,
                timestamp_from=sensor.configuration.last_baseline_selection_timestamp,
                order_by_desc=True,
            )
        except NotFoundError:
            logger.error(ERROR_MESSAGE_TSD_NOT_FOUND)

            await create_system_event(
                system.EventUncommited(
                    type=system.EventType.ALERT_CRITICAL,
                    message=ERROR_MESSAGE_TSD_NOT_FOUND,
                )
            )

            continue

        try:
            cleaned_concentrations: NDArray[
                np.float64
            ] = await services.baselines.clean_concentrations(
                concentrations=np.array([tsd.ppmv async for tsd in tsd_set])
            )
        except UnprocessableError as error:
            await create_system_event(
                system.EventUncommited(
                    type=system.EventType.ALERT_CRITICAL, message=str(error)
                )
            )

            continue

        if best_baseline := (
            await services.baselines.select_best_baseline(
                seed_baselines=seed_baselines,
                cleaned_concentrations=cleaned_concentrations,
            )
        ):
            logger.success(
                f"Changing the initial baseline for the sensor {sensor.name}."
                f"\nCurrent baseline is taken from the file: "
                f"{best_baseline.filename}"
            )
            # Update the configuration with the new baseline
            await SensorsConfigurationsRepository().update_partially(
                id_=sensor.configuration.id,
                schema=SensorConfigurationUpdatePartialSchema(
                    anomaly_detection_initial_baseline_raw=pickle.dumps(
                        best_baseline
                    )
                ),
            )

            await create_system_event(
                system.EventUncommited(
                    type=system.EventType.ALERT_SUCCESS,
                    message=(
                        "A new initial baseline is selected "
                        f"for the sensor: {sensor.name}."
                    ),
                )
            )
        else:
            message = (
                "A new initial baseline is not changed after the selection"
            )
            logger.info(message)

            await create_system_event(
                system.EventUncommited(
                    type=system.EventType.INFO, message=message
                )
            )


def initial_baseline_augmentation():
    """This function runs the initial baseline augmentation/update process.

    🚩 The flow:
    1. take all historical TSD
    2. clean concentrations.
    3. Iterate through each baseline from the seed bank
        and update with cleaned concentrations.

    ⚠️  The process runs every N seconds where N is usually ~90 days
    since the selection process is quite complicated from the
    competition perspective.
    """

    while True:
        # Defines the break for collecting enough data
        sleep(
            settings.sensors.anomaly_detection.baseline_augmentation_interval.total_seconds()  # noqa: E501
        )
        asyncio.run(_initial_baseline_augmentation())
        # await _initial_baseline_augmentation()


@transaction
async def _initial_baseline_augmentation():
    # TODO: Add other pre-feature validations

    baselines_services = services.baselines  # alias

    # Make the augmentation for each sensor and update it in the database
    async for sensor in SensorsRepository().filter():
        logger.info(f"Inital baseline augmentation for {sensor.name}...")

        try:
            tsd_set: AsyncGenerator[TsdFlat, None] = TsdRepository().filter(
                sensor_id=sensor.id, timestamp_from=None, order_by_desc=True
            )
        except NotFoundError:
            message = (
                "The initial baseline augmentation is possible "
                "only in case time series data exists in the database. "
                f"Sensor: {sensor.name}"
            )

            logger.error(message)

            # Create the system event if augmentation is not possible
            system_event: system.Event = await SystemEventsRepository().create(
                schema=system.EventUncommited(
                    type=system.EventType.ALERT_CRITICAL, message=message
                )
            )

            # Update the data lake
            data_lake.events_system.storage.append(system_event)

            return

        cleaned_concentrations: NDArray[
            np.float64
        ] = await baselines_services.clean_concentrations(
            concentrations=np.array([tsd.ppmv async for tsd in tsd_set])
        )

        # Get the updated initial baseline after the augmentation
        updated_baseline: aampi = (
            await baselines_services.initial_baseline_augment(
                sensor, cleaned_concentrations
            )
        )

        # Update the configuration with the new baseline
        await SensorsConfigurationsRepository().update_partially(
            id_=sensor.configuration.id,
            schema=SensorConfigurationUpdatePartialSchema(
                anomaly_detection_initial_baseline_raw=pickle.dumps(
                    updated_baseline
                )
            ),
        )
