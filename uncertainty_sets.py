import pandas as pd
import numpy as np

# -------------------------------
# Configuration
# -------------------------------
DATA_FILE = "hospital_disaster_continuous_dataset.csv"
HOSPITALS = ["H1", "H2", "H3"]

# Min–max box levels
MINMAX_BOX_LEVELS = [1.0, 0.75, 0.5]

# EV-centered box levels (k · std)
EV_BOX_LEVELS = [0, 1, 2]

OUTPUT_FILE = "hospital_uncertainty_sets.csv"

# -------------------------------
# Load dataset
# -------------------------------
df = pd.read_csv(DATA_FILE)

# -------------------------------
# Precompute statistics
# -------------------------------
stats = {}

for hid in HOSPITALS:
    demands = df.loc[df["hospital_id"] == hid, "demand"]
    stats[hid] = {
        "min": demands.min(),
        "max": demands.max(),
        "mean": demands.mean(),
        "std": demands.std(ddof=1),
    }

# -------------------------------
# Build uncertainty sets
# -------------------------------
rows = []

# ---- 1. Min–max box sets ----
for alpha in MINMAX_BOX_LEVELS:
    for hid in HOSPITALS:
        dmin = stats[hid]["min"]
        dmax = stats[hid]["max"]

        lower = dmin + (dmax - dmin) * (1 - alpha) / 2
        upper = dmax - (dmax - dmin) * (1 - alpha) / 2

        # integer & conservative rounding
        lower = int(np.floor(lower))
        upper = int(np.ceil(upper))

        rows.append({
            "uncertainty_type": "minmax_box",
            "level": alpha,
            "hospital_id": hid,
            "lower_bound": lower,
            "upper_bound": upper,
        })

# ---- 2. EV-centered box sets (NO clipping to max) ----
for k in EV_BOX_LEVELS:
    for hid in HOSPITALS:
        mu = stats[hid]["mean"]
        sigma = stats[hid]["std"]

        lower = max(0.0, mu - k * sigma)
        upper = mu + k * sigma

        # integer & conservative rounding
        lower = int(np.floor(lower))
        upper = int(np.ceil(upper))

        rows.append({
            "uncertainty_type": "ev_box",
            "level": k,
            "hospital_id": hid,
            "lower_bound": lower,
            "upper_bound": upper,
        })

# -------------------------------
# Save results
# -------------------------------
uncertainty_df = pd.DataFrame(rows)
uncertainty_df.to_csv(OUTPUT_FILE, index=False)

print(f"Uncertainty sets saved to {OUTPUT_FILE}")
