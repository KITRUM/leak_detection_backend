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
)
from src.domain.sensors import services as sensors_services

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


async def _select_best_baseline():
    # WARNING: Other pre-feature validations are not added

    seed_baselines: list[
        SeedBaseline
    ] = anomaly_detection_services.baselines.seed.for_select_best()

    # Select the best baseline for each sensor and update it in the database
    # if seed baseline feets the needs
    async for sensor in await sensors_services.crud.get_all():
        logger.info(f"Best baseline seelction for {sensor.name}...")

        cleaned_concentrations: NDArray[
            np.float64
        ] = await anomaly_detection_services.baselines.clean_concentrations(
            sensor=sensor,
            last_baseline_selection_timestamp=None,
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
            await sensors_services.crud.update(
                sensor_id=sensor.id,
                configuration_update_schema=SensorConfigurationUpdatePartialSchema(  # noqa: E501
                    anomaly_detection_initial_baseline_raw=pickle.dumps(
                        best_baseline
                    )
                ),
            )
