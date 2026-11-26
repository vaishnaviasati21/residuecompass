import json
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"


class MockForecastProvider:
    def get(self, village_id: str):
        data = json.loads((SEED_DIR / "forecasts.json").read_text(encoding="utf-8"))
        return data.get(village_id)


def get_forecast_provider():
    # Later: return the real ML provider when DEMO_MODE is false
    return MockForecastProvider()