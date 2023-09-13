"""
This module is created in order to provide some dev features
that should be involved onlly if the DEBUG mode is turned on.

It is not coupled with the rest of the project's business logic
for better segregation. In case we don't need it anymore the folder
can be easily removed from sources.
"""

from src.domain.anomaly_detection import AnomalyDetectionRepository
from src.domain.estimation import EstimationsSummariesRepository
from src.domain.events.sensors import SensorsEventsRepository
from src.domain.simulation import SimulationDetectionRatesRepository
from src.domain.tsd import TsdRepository
from src.infrastructure.database import transaction


@transaction
async def reset_the_database():
    """This function is used as a debug hook which is called
    on each application startup if the mode is DEBUG.
    """

    await AnomalyDetectionRepository().delete_all()
    await TsdRepository().delete_all()
    await SimulationDetectionRatesRepository().delete_all()
    await EstimationsSummariesRepository().delete_all()
    await SensorsEventsRepository().delete_all()
