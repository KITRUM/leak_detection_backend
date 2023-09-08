from sqladmin import ModelView

from src.infrastructure.database import (
    SensorsConfigurationsTable,
    SensorsTable,
)

__all__ = ("SensorsConfigurationsAdminView", "SensorsAdminView")


class SensorsConfigurationsAdminView(
    ModelView, model=SensorsConfigurationsTable
):
    name = "Sensor configuration"
    name_plural = "Sensors configurations"
    column_list = ("id", "interactive_feedback_mode", "sensor")
    column_searchable_list = ("interactive_feedback_mode", "sensor")
    colsort = ("id", "interactive_feedback_mode", "sensor")
    column_details_exclude_list = ("anomaly_detection_initial_baseline_raw",)


class SensorsAdminView(ModelView, model=SensorsTable):
    name = "Sensor"
    name_plural = "Sensors"
    column_list = ("id", "name", "configuration", "template")
    column_searchable_list = ("name", "configuration", "template")
    column_sortable_list = ("id", "name", "configuration", "template")
    column_details_exclude_list = (
        "time_series_data",
        "estimation_summary_set",
        "events",
    )
