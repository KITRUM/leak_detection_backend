import pickle

from stumpy.aampi import aampi

from src.config import settings

__all__ = ("INITIAL_BASELINE_HIGH", "INITIAL_BASELINE_LOW")


# Load initial baselines
# --------------------------------------------------------------
INITIAL_BASELINE_HIGH: aampi = pickle.load(
    open(f"{settings.seed_dir}/baselines/high.mpstream", "rb")
)
INITIAL_BASELINE_LOW: aampi = pickle.load(
    open(f"{settings.seed_dir}/baselines/low.mpstream", "rb")
)
