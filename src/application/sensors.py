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
from time import sleep
from typing import Coroutine

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from stumpy import aampi

from src.config import settings
from src.domain.anomaly_detection import SeedBaseline
from src.domain.anomaly_detection import services as anomaly_detection_services
from src.domain.sensors import (
    Sensor,
    SensorBase,
    SensorConfigurationUncommited,
    SensorConfigurationUpdatePartialSchema,
    SensorCreateSchema,
    SensorsConfigurationsRepository,
    SensorsRepository,
)
from src.domain.sensors import services as sensors_services
from src.domain.tsd import TsdFlat
from src.domain.tsd import services as tsd_services
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
async def create(template_id: int, sensor_payload: SensorBase) -> Sensor:
    """This function takes care about the sensor creation.
    The sensor creation consist of:
        1. creating the default sensor's configuration
            1.1. the initial baseline from seed files
                 is added to the configuration
        2. creating the sensor and attaching the configuration to it
    """

    anomaly_detection_initial_baseline: aampi = (
        anomaly_detection_services.baselines.seed.by_level(level="high")
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

    return await sensors_services.crud.create(create_schema)


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


@transaction
async def _select_best_baseline():
    # WARNING: Other pre-feature validations are not added

    seed_baselines: list[
        SeedBaseline
    ] = anomaly_detection_services.baselines.seed.for_select_best()

    # Select the best baseline for each sensor and update it in the database
    # if seed baseline feets the needs
    async for sensor in SensorsRepository().filter():
        logger.info(f"Best baseline seelction for {sensor.name}...")

        try:
            tsd_set: list[TsdFlat] = await tsd_services.get_last_set_from(
                sensor_id=sensor.id,
                timestamp=sensor.configuration.last_baseline_selection_timestamp,
            )
        except NotFoundError:
            raise UnprocessableError(
                message=(
                    "The initial baseline augmentation is possible "
                    "only in case time series data exists in the database. "
                    f"Sensor: {sensor.name}"
                )
            )

        cleaned_concentrations: NDArray[
            np.float64
        ] = await anomaly_detection_services.baselines.clean_concentrations(
            concentrations=np.array([tsd.ppmv for tsd in tsd_set])
        )

        if best_baseline := (
            await anomaly_detection_services.baselines.select_best_baseline(
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


@transaction
async def _initial_baseline_augmentation():
    # TODO: Add other pre-feature validations

    baselines_services = anomaly_detection_services.baselines  # alias

    # Make the augmentation for each sensor and update it in the database
    async for sensor in SensorsRepository().filter():
        logger.info(f"Inital baseline augmentation for {sensor.name}...")

        try:
            tsd_set: list[TsdFlat] = await tsd_services.get_last_set_from(
                sensor_id=sensor.id, timestamp=None
            )
        except NotFoundError:
            raise UnprocessableError(
                message=(
                    "The initial baseline augmentation is possible "
                    "only in case time series data exists in the database. "
                    f"Sensor: {sensor.name}"
                )
            )

        cleaned_concentrations: NDArray[
            np.float64
        ] = await baselines_services.clean_concentrations(
            concentrations=np.array([tsd.ppmv for tsd in tsd_set])
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
