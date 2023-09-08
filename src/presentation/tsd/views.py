from sqladmin import ModelView

from src.infrastructure.database import TimeSeriesDataTable

__all__ = ("TimeSeriesDataAdminView",)


class TimeSeriesDataAdminView(ModelView, model=TimeSeriesDataTable):
    name = "Time Series Data"
    name_plural = "Time Series Data items"
    column_list = ("id", "sensor", "ppmv", "timestamp")
    column_searchable_list = ("sensor",)
    column_sortable_list = ("id", "sensor", "ppmv", "timestamp")
    column_labels = {
        "ppmv": "concentration, ppmv (rounded to 2 decimal places)"
    }
    column_formatters = {
        "ppmv": lambda model, name: f"{getattr(model, 'ppmv'):.2f}",
    }
