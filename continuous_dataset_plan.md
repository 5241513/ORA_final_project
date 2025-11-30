# Continuous, Correlated Demand Dataset Plan

## Objectives
- Generate a large sample (e.g., 1,000 scenarios) of hospital demand vectors using continuous distributions.
- Encode correlations between hospitals and between disaster drivers by sampling from multivariate normals.
- Allow optional noise and severity drivers so ellipsoidal uncertainty sets become meaningful.
- Persist both the raw scenario samples and aggregated statistics for downstream notebooks.

## Proposed data-generating process
1. **Severity latent factors**
   - Global hazard severity `G ~ LogNormal(mu=2.8, sigma=0.35)` controls overall scale.
   - Regional shocks `R ~ N(0, Sigma_R)` with a 3x3 covariance to capture spatial correlations among hospitals.
   - Scenario-specific noise `eps ~ N(0, sigma_eps^2 I)` for idiosyncratic variation.
2. **Hospital baselines**
   - Baseline demand vector `b = [20, 15, 12]` representing typical daily surges.
   - Hospital sensitivity coefficients `alpha = [1.0, 0.85, 0.75]` multiply the global severity and add to baselines.
3. **Demand construction**
   - `demand = clip(b + alpha * G + R + eps, min=0)`.
   - Round to integers if desired (keep float for modeling, round only when storing counts).
4. **Scenario metadata**
   - Sample disaster type labels from a categorical distribution tied to severity quantiles (mild, moderate, extreme).
   - Assign probabilities via kernel density estimate or frequency normalization (probability sums to 1 across samples).
5. **Capacities & costs**
   - Reuse existing hospital capacities and per-unit costs for compatibility.

## Files to produce
1. `continuous_dataset.py` (new generator script):
   - Generates scenarios with a reproducible random seed.
   - Saves `hospital_demand_continuous.csv` with columns: `scenario_id, probability, disaster_type, hospital_id, demand, severity_score, ...`.
   - Optionally saves summary stats JSON for quick reference.
2. `continuous_models.ipynb`:
   - Loads the new dataset, visualizes distributions (histograms, correlation heatmap).
   - Rebuilds deterministic OR, SP, and RO models.
   - Adds at least two RO variants (box/budget vs ellipsoidal) for comparison.

## Next steps
1. Finalize parameter values ( covariances, noise levels, number of scenarios ).
2. Implement generator script and validate outputs.
3. Build the new notebook with distribution analysis and optimization studies.
