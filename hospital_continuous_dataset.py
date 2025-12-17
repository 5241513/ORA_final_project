import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List

# -------------------------
# Discrete data 
# -------------------------
hospitals = {
    "H1": ("Central Hospital", 220, 2.0, 2.7),
    "H2": ("North Clinic", 160, 2.2, 3.0),
    "H3": ("South Medical Center", 140, 1.8, 2.43)
}

shortage_penalty = 8.0

scenarios = {
    "S0": ("no_disaster",  [6, 5, 4], 0.65),
    "S1": ("mild_flood",  [60, 45, 35], 0.05),
    "S2": ("moderate_flood", [85, 65, 45], 0.04),
    "S3": ("earthquake", [110, 85, 65], 0.05),
    "S4": ("heatwave", [70, 55, 45], 0.1),
    "S5": ("severe_storm", [95, 75, 55], 0.05),
    "S6": ("major_earthquake", [150, 110, 90], 0.04),
    "S7": ("multi_wave_pandemic", [200, 140, 120], 0.02)
}

# -------------------------
# Continuous dataset 
# -------------------------
RNG = np.random.default_rng(seed=42)
NUM_CONTINUOUS_SAMPLES_PER_SCENARIO = 50  
# generate 50 draws per discrete scenario

# Covariance among hospitals 
BASE_COV = np.array([
    [60.0, 38.0, 32.0],
    [38.0, 55.0, 29.0],
    [32.0, 29.0, 45.0]
])

@dataclass
class ScenarioDraw:
    scenario_id: str
    disaster_type: str
    hospital_id: str
    hospital_name: str
    capacity_beds: int
    allocation_cost_per_unit: float
    demand: float
    regional_component: float
    idiosyncratic_component: float
    scenario_probability: float
    shortage_penalty_per_unit: float
    surge_cost_per_unit: float

# -------------------------
# Generate continuous draws
# -------------------------
rows = []

hospital_ids = list(hospitals.keys())
num_hospitals = len(hospital_ids)

for sid, (dtype, demands, probability) in scenarios.items():
    # Convert discrete demands to numpy array
    base_demand = np.array(demands, dtype=float)
    
    # Generate continuous draws per scenario
    for sample_idx in range(NUM_CONTINUOUS_SAMPLES_PER_SCENARIO):
        # Regional correlated component
        regional = RNG.multivariate_normal(mean=np.zeros(num_hospitals), cov=BASE_COV)
        # Idiosyncratic component
        idio = RNG.normal(0.0, 5.0, size=num_hospitals)  # standard deviation = 5
        # Continuous demand
        continuous_demand = base_demand + regional + idio
        continuous_demand = np.clip(continuous_demand, 0, None)  # no negative demand
        # demand should be int
        continuous_demand = np.round(continuous_demand).astype(int)
        
        for i, hid in enumerate(hospital_ids):
            hname, capacity, alloc_cost, surge_cost = hospitals[hid]
            rows.append({
                "scenario_id": f"{sid}_{sample_idx:03d}",
                "scenario_probability": probability / NUM_CONTINUOUS_SAMPLES_PER_SCENARIO,  # split probability
                "disaster_type": dtype,
                "hospital_id": hid,
                "hospital_name": hname,
                "capacity_beds": capacity,
                "demand": round(continuous_demand[i], 2),
                "allocation_cost_per_unit": alloc_cost,
                "shortage_penalty_per_unit": shortage_penalty,
                "surge_cost_per_unit": surge_cost,
                "regional_component": round(regional[i], 2),
                "idiosyncratic_component": round(idio[i], 2)
            })

df = pd.DataFrame(rows)
df.to_csv("hospital_disaster_continuous_dataset.csv", index=False)

print("hospital_disaster_continuous_dataset.csv created!")
