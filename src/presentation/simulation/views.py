from sqladmin import ModelView

from src.infrastructure.database import SimulationDetectionsTable

__all__ = ("SimulationDetectionRatesAdminView",)


class SimulationDetectionRatesAdminView(
    ModelView, model=SimulationDetectionsTable
):
    name = "Simulation"
    name_plural = "Simulations"
    column_list = ("id", "leakage", "anomaly_detection")
    column_searchable_list = ("leakage", "anomaly_detection")
    column_sortable_list = ("id", "leakage", "anomaly_detection")
    column_details_exclude_list = ("concentrations",)
    form_excluded_columns = ("concentrations",)
