"""
Lightweight REST API Router Adapter for Residue Compass Part 4.
Designed for Part 1 to easily mount into FastAPI or Flask applications without external dependencies.
"""

from typing import Dict, Any, List
from residue_compass_economics.schemas import (
    VillageStrawForecast,
    VillageEconomicInput,
    Buyer,
    Baler,
    Truck,
    MatchBooking,
    StressScenario,
)
from residue_compass_economics.config import EconomicsConfig, MatchingConfig
from residue_compass_economics.service import (
    calculate_decision,
    run_what_if,
    run_matching,
    calculate_impact,
    run_stress_tests,
    validate_project_data,
)


class Part4APIRouter:
    """
    Standardized callable request handlers implementing Part 4 API specification.
    Can be mapped to FastAPI routers or Flask blueprints in Part 1.
    """

    @staticmethod
    def handle_calculate_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/economics/decision"""
        forecast = VillageStrawForecast.from_dict(payload["forecast"])
        econ_input = VillageEconomicInput.from_dict(payload["economic_input"]) if "economic_input" in payload else None
        config = EconomicsConfig.from_dict(payload["assumptions"]) if "assumptions" in payload else None
        
        decision = calculate_decision(forecast, econ_input, config)
        return decision.to_dict()

    @staticmethod
    def handle_what_if(payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/economics/what-if"""
        forecast = VillageStrawForecast.from_dict(payload["forecast"])
        econ_input = VillageEconomicInput.from_dict(payload["economic_input"])
        overrides = payload.get("overrides", {})
        config = EconomicsConfig.from_dict(payload["assumptions"]) if "assumptions" in payload else None

        result = run_what_if(forecast, econ_input, overrides, config)
        return result.to_dict()

    @staticmethod
    def handle_run_matching(payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/matching/run"""
        forecasts = [VillageStrawForecast.from_dict(f) for f in payload.get("forecasts", [])]
        buyers = [Buyer.from_dict(b) for b in payload.get("buyers", [])]
        balers = [Baler.from_dict(bal) for bal in payload.get("balers", [])]
        trucks = [Truck.from_dict(t) for t in payload.get("trucks", [])]
        m_cfg = MatchingConfig.from_dict(payload["matching_config"]) if "matching_config" in payload else None
        e_cfg = EconomicsConfig.from_dict(payload["economics_config"]) if "economics_config" in payload else None

        result = run_matching(forecasts, buyers, balers, trucks, m_cfg, e_cfg)
        return result.to_dict()

    @staticmethod
    def handle_calculate_impact(payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/economics/impact"""
        forecasts = [VillageStrawForecast.from_dict(f) for f in payload.get("forecasts", [])]
        bookings = [MatchBooking.from_dict(b) for b in payload.get("bookings", [])]
        config = EconomicsConfig.from_dict(payload["assumptions"]) if "assumptions" in payload else None

        impact = calculate_impact(forecasts, bookings, config)
        return impact.to_dict()

    @staticmethod
    def handle_stress_test(payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/validation/stress-test"""
        forecast = VillageStrawForecast.from_dict(payload["forecast"])
        econ_input = VillageEconomicInput.from_dict(payload["economic_input"])
        scenarios = [StressScenario(**s) for s in payload.get("scenarios", [])] if "scenarios" in payload else None
        config = EconomicsConfig.from_dict(payload["assumptions"]) if "assumptions" in payload else None

        report = run_stress_tests(forecast, econ_input, scenarios, config)
        return report.to_dict()

    @staticmethod
    def handle_validate_project_data(payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/validation/project-data"""
        forecasts = [VillageStrawForecast.from_dict(f) for f in payload.get("forecasts", [])]
        buyers = [Buyer.from_dict(b) for b in payload.get("buyers", [])]
        balers = [Baler.from_dict(bal) for bal in payload.get("balers", [])]
        trucks = [Truck.from_dict(t) for t in payload.get("trucks", [])]

        result = validate_project_data(forecasts, buyers, balers, trucks)
        return result.to_dict()
