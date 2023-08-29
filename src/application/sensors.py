import pickle

from stumpy import aampi

from src.domain.anomaly_detection import services as anomaly_detection_services
from src.domain.sensors import (
    Sensor,
    SensorBase,
    SensorConfigurationUncommited,
    SensorCreateSchema,
)
from src.domain.sensors import services as sensors_services


async def create(template_id: int, sensor_payload: SensorBase) -> Sensor:
    """This function takes care about the sensor creation.
    The sensor creation consist of:
        1. creating the default sensor's configuration
            1.1. the initial baseline from seed files
                 is added to the configuration
        2. creating the sensor and attaching the configuration to it
    """

    anomaly_detection_initial_baseline: aampi = (
        anomaly_detection_services.baselines.get_from_seed(level="high")
    )

    initial_baseline_flat: bytes = pickle.dumps(
        anomaly_detection_initial_baseline
    )

    create_schema = SensorCreateSchema(
        configuration_uncommited=SensorConfigurationUncommited(
            interactive_feedback_mode=False,
            initial_anomaly_detection_baseline=initial_baseline_flat,
        ),
        template_id=template_id,
        sensor_payload=sensor_payload,
    )

    return await sensors_services.create(create_schema)
