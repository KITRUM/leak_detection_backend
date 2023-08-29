"""
The selection baseline feature.

Every `settings.anomaly_detection.baseline_selection_limit`
the background task goes to the baselines bank which placed in the seed/ fodler
and start the selection of the BEST baseline for this range of TSD items.

⚡️ The task is CPU-bound so it runs in a separate process.
"""


def process():
    """This function runs the baseline selection process"""

    pass
