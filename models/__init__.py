"""Machine-learning package. Import submodules directly to avoid loading joblib at package import time."""

__all__ = ["PerformancePredictor"]


def __getattr__(name: str):
    if name == "PerformancePredictor":
        from models.predictor import PerformancePredictor

        return PerformancePredictor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
