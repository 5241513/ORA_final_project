import pandas as pd

# Base data
hospitals = {
    "H1": ("Central Hospital", 250, 2.0),
    "H2": ("North Clinic", 180, 2.2),
    "H3": ("South Medical Center", 150, 1.8)
}

shortage_penalty = 8.0

# name, demands for H1, H2, H3 and scenario probability
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

rows = []

for sid, (dtype, demands, probability) in scenarios.items():
    for i, hid in enumerate(["H1", "H2", "H3"]):
        hname, capacity, alloc_cost = hospitals[hid]
        demand = demands[i]
        probability = probability
        
        rows.append({
            "scenario_id": sid,
            "scenario_probability": probability,
            "disaster_type": dtype,
            "hospital_id": hid,
            "hospital_name": hname,
            "capacity_beds": capacity,
            "demand": demand,
            "allocation_cost_per_unit": alloc_cost,
            "shortage_penalty_per_unit": shortage_penalty
        })

df = pd.DataFrame(rows)
df.to_csv("hospital_disaster_dataset.csv", index=False)

print("hospital_disaster_dataset.csv created!")