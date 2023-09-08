from sqladmin import ModelView

from src.infrastructure.database import SimulationDetectionRatesTable

__all__ = ("SimulationDetectionRatesAdminView",)


class SimulationDetectionRatesAdminView(
    ModelView, model=SimulationDetectionRatesTable
):
    name = "Simulation"
    name_plural = "Simulations"
    column_list = ("id", "leakage", "rate", "anomaly_detection")
    column_searchable_list = ("leakage", "rate", "anomaly_detection")
    column_sortable_list = ("id", "leakage", "rate", "anomaly_detection")
    column_details_exclude_list = ("concentrations",)
    form_excluded_columns = ("concentrations",)
