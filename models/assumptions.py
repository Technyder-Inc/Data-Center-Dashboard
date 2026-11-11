"""Model assumptions that used to be hard-coded. Defaults reproduce the original behaviour exactly."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from models.forecast import Expansion
from utils.validation import LIMITS


@dataclass(frozen=True)
class Assumptions:
    high_growth_pct: float = 25.0
    efficiency_pct: float = 10.0
    expansion_site: str = "DC3"
    expansion_power_mw: float = 4.0
    expansion_cooling_mwe: float = 4.0
    expansion_racks: int = 100
    expansion_month: int = 12
    weight_timing: float = 35.0
    weight_peak: float = 25.0
    weight_risk: float = 15.0
    weight_fit: float = 15.0
    weight_cost: float = 10.0
    score_medium: float = 40.0
    score_high: float = 70.0
    score_critical: float = 100.0
    lead_time_months: int = 6
    immediate_months: int = 6
    caution_pct: float = 70.0
    whatif_efficiency_pct: float = 10.0
    whatif_delay_months: int = 6

    def weights(self) -> dict[str, float]:
        return {"timing": self.weight_timing / 100.0, "peak_utilization": self.weight_peak / 100.0,
                "risk_level": self.weight_risk / 100.0, "resource_fit": self.weight_fit / 100.0, "cost": self.weight_cost / 100.0}

    def risk_scores(self) -> dict[str, float]:
        return {"Low": 0.0, "Medium": self.score_medium, "High": self.score_high, "Critical": self.score_critical}

    def expansion(self) -> Expansion:
        return Expansion(self.expansion_site, self.expansion_power_mw, self.expansion_cooling_mwe, float(self.expansion_racks), self.expansion_month)


DEFAULT_ASSUMPTIONS = Assumptions()


def validate_assumptions(a: Assumptions, site_ids: list[str]) -> list[str]:
    errors = []
    nums = [v for v in vars(a).values() if isinstance(v, (int, float))]
    if any(not isfinite(v) for v in nums):
        return ["All values must be finite numbers"]
    if not LIMITS["portfolio_growth_pct"][0] <= a.high_growth_pct <= LIMITS["portfolio_growth_pct"][1]:
        errors.append("High Growth rate must be within %g to %g percent" % LIMITS["portfolio_growth_pct"])
    if not LIMITS["efficiency_pct"][0] <= a.efficiency_pct <= LIMITS["efficiency_pct"][1]:
        errors.append("Efficiency reduction must be within %g to %g percent" % LIMITS["efficiency_pct"])
    if a.expansion_site not in site_ids:
        errors.append("Expansion preset facility is not in the dataset")
    for value, name, label in ((a.expansion_power_mw, "expansion_power_mw", "power"), (a.expansion_cooling_mwe, "expansion_cooling_mwe", "cooling"),
                               (a.expansion_racks, "expansion_racks", "racks")):
        if not LIMITS[name][0] <= value <= LIMITS[name][1]:
            errors.append(f"Expansion preset {label} must be within %g to %g" % LIMITS[name])
    if not 0 <= a.expansion_month <= 36 or a.expansion_month % 1:
        errors.append("Expansion preset activation month must be a whole number from 0 to 36")
    ws = [a.weight_timing, a.weight_peak, a.weight_risk, a.weight_fit, a.weight_cost]
    if min(ws) < 0 or abs(sum(ws) - 100.0) > 0.01:
        errors.append(f"Ranking weights must be nonnegative and total 100 (currently {sum(ws):g})")
    if not 0 <= a.score_medium <= a.score_high <= a.score_critical <= 100:
        errors.append("Risk scores must satisfy 0 <= Medium <= High <= Critical <= 100")
    if not 0 <= a.lead_time_months <= 36 or not 0 <= a.immediate_months <= 36:
        errors.append("Lead time and immediate window must be 0 to 36 months")
    if not 0 < a.caution_pct < 100:
        errors.append("Caution band start must be between 0 and 100 percent")
    if not 0 < a.whatif_efficiency_pct < 100 or not 1 <= a.whatif_delay_months <= 36:
        errors.append("What-if efficiency must be above 0 and below 100 percent and the delay 1 to 36 months")
    return errors
