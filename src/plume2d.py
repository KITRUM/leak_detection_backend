from datetime import datetime

import numpy as np

from src.domain.anomaly_detection import AnomalyDetection, AnomalyDeviation
from src.domain.simulation import SimulationDetectionRateFlat
from src.domain.tsd import TsdFlat


class SimulationConfiguration:
    """This class includes the simulation configuration.
    Just for the sake of simplicity, we will use a single
    class to represent the simulation configuration.
    Just create another attribute if you need to add
    another configuration.
    """

    config_name = "value"


anomaly_detection = AnomalyDetection(
    id=1,
    time_series_data=TsdFlat(
        id=1,
        ppmv=np.float64(1.0),
        timestamp=datetime.now(),
        sensor_id=1,
    ),
    value=AnomalyDeviation.CRITICAL,
)


def simulate(
    anomaly_detection: AnomalyDetection,
) -> list[SimulationDetectionRateFlat]:
    # anomaly_detection.time_series_data

    raise NotImplementedError
