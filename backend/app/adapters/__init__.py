"""
Adapters package.
Provides mock_* and real_* providers for every external service.
In DEMO_MODE the app always uses mock providers.
In production set DEMO_MODE=false and the real providers call ml/predict.py
and economics/decide.py via the adapters below.
"""
from app.core.config import settings


class MockForecastProvider:
    """Returns the fixed seed forecast for a village."""
    def get(self, village_id: str):
        from app.services.queries import get_forecast
        return get_forecast(village_id)


class RealForecastProvider:
    """Calls the ML module. Only used when DEMO_MODE=false."""
    def get(self, village_id: str):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../ml"))
        try:
            from predict import predict_village  # type: ignore
            return predict_village(village_id)
        except ImportError:
            raise RuntimeError("ml/predict.py not found – switch to DEMO_MODE=true")


def get_forecast_provider():
    if settings.DEMO_MODE:
        return MockForecastProvider()
    return RealForecastProvider()


class MockDecisionProvider:
    def get(self, village_id: str, assumptions=None):
        from app.services.queries import get_decision
        return get_decision(village_id)


class RealDecisionProvider:
    def get(self, village_id: str, assumptions=None):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../economics"))
        try:
            from decide import decide  # type: ignore
            return decide(village_id, assumptions)
        except ImportError:
            raise RuntimeError("economics/decide.py not found – switch to DEMO_MODE=true")


def get_decision_provider():
    if settings.DEMO_MODE:
        return MockDecisionProvider()
    return RealDecisionProvider()
