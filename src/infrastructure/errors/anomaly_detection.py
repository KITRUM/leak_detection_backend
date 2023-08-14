from .base import BaseError

__all__ = ("AnomalyDetectionMatrixProfileError",)


class AnomalyDetectionMatrixProfileError(BaseError):
    def __init__(self, counter) -> None:
        message = (
            "Anomaly detection processing is skipped "
            "due to not enough elements in the matrix profile. "
            f"Current amount: {counter}"
        )

        super().__init__(message=message, status_code=422)
