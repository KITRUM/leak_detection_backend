from src.domain.simulation import RegressionProcessor
from src.domain.templates import Template

from . import deep_blow_opened_template


def get_processor_callback(
    template: Template,
) -> RegressionProcessor:
    if template.z_roof is None:
        return deep_blow_opened_template.get_concentration
    else:
        raise NotImplementedError(
            "Only opened template deep blow regression is available"
        )
