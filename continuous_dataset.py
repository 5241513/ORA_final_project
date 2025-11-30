"""Generate a continuous, correlated disaster demand dataset.

The script produces a long-form CSV similar to the discrete dataset but
with 1,000 (configurable) scenarios sampled from continuous distributions
with correlated hospital shocks. Probabilities are inferred from hazard
weights and severity draws so downstream stochastic/robust models can use
ellipsoidal or polyhedral uncertainty sets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_CSV = Path("hospital_demand_continuous.csv")
SUMMARY_JSON = Path("hospital_demand_continuous_summary.json")
RNG = np.random.default_rng(seed=42)
NUM_SCENARIOS = 1000
INCLUDE_BASELINE_SCENARIO = True
BASELINE_WEIGHT = 1.0
BASELINE_PROBABILITY_SHARE = 0.35  # portion of probability mass reserved for the calm scenario
BASELINE_DEMAND_SCALE = 0.35
BASELINE_MIN_DEMAND = np.array([6.0, 4.5, 3.5])

hospitals: Dict[str, Dict[str, float]] = {
    "H1": {"name": "Central Hospital", "capacity": 250, "alloc_cost": 2.0},
    "H2": {"name": "North Clinic", "capacity": 180, "alloc_cost": 2.2},
    "H3": {"name": "South Medical Center", "capacity": 150, "alloc_cost": 1.8},
}

baseline_demand = np.array([20.0, 15.0, 12.0])
severity_sensitivity = np.array([1.00, 0.85, 0.70])

# Base covariance encodes spatial correlation among the three hospitals.
BASE_COV = np.array(
    [
        [60.0, 38.0, 32.0],
        [38.0, 55.0, 29.0],
        [32.0, 29.0, 45.0],
    ]
)


def _hazard_catalog() -> pd.DataFrame:
    """Return hazard definitions with sampling weights and noise scales."""
    return pd.DataFrame(
        [
            {
                "hazard_type": "seasonal_flu",
                "weight": 0.45,
                "lognorm_mu": 2.1,
                "lognorm_sigma": 0.25,
                "region_scale": 0.8,
                "idio_sigma": 6.0,
            },
            {
                "hazard_type": "coastal_storm",
                "weight": 0.25,
                "lognorm_mu": 2.5,
                "lognorm_sigma": 0.28,
                "region_scale": 1.0,
                "idio_sigma": 7.5,
            },
            {
                "hazard_type": "earthquake",
                "weight": 0.15,
                "lognorm_mu": 2.9,
                "lognorm_sigma": 0.35,
                "region_scale": 1.3,
                "idio_sigma": 9.0,
            },
            {
                "hazard_type": "pandemic_wave",
                "weight": 0.15,
                "lognorm_mu": 3.2,
                "lognorm_sigma": 0.32,
                "region_scale": 1.5,
                "idio_sigma": 11.0,
            },
        ]
    )


@dataclass
class ScenarioDraw:
    scenario_id: str
    hazard_type: str
    severity_score: float
    global_severity: float
    regional_component: np.ndarray
    idiosyncratic_component: np.ndarray
    raw_probability_weight: float
    demand_vector: np.ndarray


def _build_baseline_draw() -> ScenarioDraw:
    """Construct a no-disaster reference scenario for calibration."""
    zero_component = np.zeros(len(hospitals))
    calm_demand = np.maximum(baseline_demand * BASELINE_DEMAND_SCALE, BASELINE_MIN_DEMAND)
    return ScenarioDraw(
        scenario_id="CSBASE",
        hazard_type="no_event",
        severity_score=0.0,
        global_severity=0.0,
        regional_component=zero_component,
        idiosyncratic_component=zero_component,
        raw_probability_weight=BASELINE_WEIGHT,
        demand_vector=calm_demand,
    )


def sample_scenarios(num_scenarios: int, include_baseline: bool = INCLUDE_BASELINE_SCENARIO) -> List[ScenarioDraw]:
    hazards = _hazard_catalog()
    hazard_probs = hazards["weight"].values / hazards["weight"].sum()

    draws: List[ScenarioDraw] = []

    num_random_draws = num_scenarios - (1 if include_baseline else 0)
    if num_random_draws < 0:
        raise ValueError("num_scenarios must be >= 1 when include_baseline is True")

    if include_baseline:
        draws.append(_build_baseline_draw())

    for idx in range(num_random_draws):
        hazard_idx = RNG.choice(len(hazards), p=hazard_probs)
        hazard = hazards.iloc[hazard_idx]
        hazard_type = hazard["hazard_type"]

        global_severity = RNG.lognormal(mean=hazard["lognorm_mu"], sigma=hazard["lognorm_sigma"])
        severity_score = float(np.log1p(global_severity))

        regional = RNG.multivariate_normal(
            mean=np.zeros(len(hospitals)), cov=hazard["region_scale"] * BASE_COV
        )
        idiosyncratic = RNG.normal(0.0, hazard["idio_sigma"], size=len(hospitals))

        demand = baseline_demand + severity_sensitivity * global_severity + regional + idiosyncratic
        demand = np.clip(demand, 0, None)

        probability_weight = float(hazard["weight"] * (severity_score + 1e-6))

        draws.append(
            ScenarioDraw(
                scenario_id=f"CS{idx:04d}",
                hazard_type=hazard_type,
                severity_score=severity_score,
                global_severity=float(global_severity),
                regional_component=regional,
                idiosyncratic_component=idiosyncratic,
                raw_probability_weight=probability_weight,
                demand_vector=demand,
            )
        )

    return draws


def build_dataframe(draws: List[ScenarioDraw]) -> pd.DataFrame:
    weights = np.array([d.raw_probability_weight for d in draws])
    probabilities = weights / weights.sum()

    if INCLUDE_BASELINE_SCENARIO and BASELINE_PROBABILITY_SHARE is not None:
        baseline_indices = [idx for idx, draw in enumerate(draws) if draw.scenario_id == "CSBASE"]
        if baseline_indices:
            baseline_idx = baseline_indices[0]
            share = float(np.clip(BASELINE_PROBABILITY_SHARE, 0.0, 0.95))
            baseline_current = probabilities[baseline_idx]
            remaining_mass = 1.0 - share
            residual = 1.0 - baseline_current
            if residual <= 0:
                probabilities[:] = 0.0
                probabilities[baseline_idx] = 1.0
            else:
                probabilities = probabilities * (remaining_mass / residual)
                probabilities[baseline_idx] = share

    rows = []
    hospital_items = list(hospitals.items())
    for draw, probability in zip(draws, probabilities):
        for hospital_idx, (hid, info) in enumerate(hospital_items):
            rows.append(
                {
                    "scenario_id": draw.scenario_id,
                    "scenario_probability": probability,
                    "disaster_type": draw.hazard_type,
                    "severity_score": draw.severity_score,
                    "hospital_id": hid,
                    "hospital_name": info["name"],
                    "capacity_beds": info["capacity"],
                    "allocation_cost_per_unit": info["alloc_cost"],
                    "global_severity": draw.global_severity,
                    "regional_component": float(draw.regional_component[hospital_idx]),
                    "idiosyncratic_component": float(draw.idiosyncratic_component[hospital_idx]),
                    "demand": float(np.round(draw.demand_vector[hospital_idx], 2)),
                    "shortage_penalty_per_unit": 8.0,
                }
            )

    return pd.DataFrame(rows)


def summarize_dataset(df: pd.DataFrame) -> Dict[str, float]:
    scenario_probs = df[["scenario_id", "scenario_probability"]].drop_duplicates()
    demand_stats = df.groupby("hospital_id")["demand"].describe(percentiles=[0.5, 0.9, 0.99])
    correlation_matrix = (
        df.pivot_table(index="scenario_id", columns="hospital_id", values="demand")
        .corr()
        .round(3)
    )

    return {
        "num_scenarios": int(scenario_probs.shape[0]),
        "probability_sum": float(scenario_probs["scenario_probability"].sum()),
        "demand_stats": demand_stats.round(2).to_dict(),
        "demand_correlation": correlation_matrix.to_dict(),
    }


def main() -> None:
    draws = sample_scenarios(NUM_SCENARIOS)
    df = build_dataframe(draws)
    df.to_csv(OUTPUT_CSV, index=False)
    summary = summarize_dataset(df)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {OUTPUT_CSV} with {len(draws)} scenarios × {len(hospitals)} hospitals")
    print(f"Probability sum: {summary['probability_sum']:.6f}")


if __name__ == "__main__":
    main()
