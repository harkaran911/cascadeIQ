"""
CascadeIQ — Phase 2: Flood Risk Training Dataset Generator
============================================================
Generates 10,000 synthetic samples using domain-informed hydrology logic
based on Punjab / Sutlej basin characteristics.

Why synthetic data?
  Real labeled flood-risk datasets for Punjab don't exist in a clean,
  publicly accessible form. So we encode real flood science into the
  generation logic — this is a standard technique called domain-informed
  data synthesis used in climate, disaster, and medical ML.

Run:
  python generate_dataset.py

Output:
  data/flood_training_data.csv
"""

import numpy as np
import pandas as pd
import os

# Fix the random seed so you get the same dataset every time you run this.
# Without this, the data would be different every run → model results
# would vary → hard to debug. Always seed your RNG in ML.
np.random.seed(42)

N = 10_000  # number of training samples

print("=" * 60)
print("CascadeIQ — Flood Risk Dataset Generator")
print("=" * 60)
print(f"\nGenerating {N:,} samples...")


# ─────────────────────────────────────────────────────────────
# STEP 1: Seasonal distribution
# ─────────────────────────────────────────────────────────────
# Punjab has 4 hydrological seasons. We generate data that reflects
# real seasonal patterns so the model learns seasonal context.
# 30% dry | 25% pre-monsoon | 35% monsoon | 10% post-monsoon

seasons = np.random.choice(
    ['dry', 'pre_monsoon', 'monsoon', 'post_monsoon'],
    size=N,
    p=[0.30, 0.25, 0.35, 0.10]
)


# ─────────────────────────────────────────────────────────────
# STEP 2: Feature generation
# Each feature uses a probability distribution that matches real
# observed ranges for that season in Punjab.
#
# exponential() → right-skewed, good for rare-event quantities like rainfall
# beta()        → bounded 0-1, good for normalized quantities
# triangular()  → bounded with a known mode, good for elevation
# lognormal()   → right-skewed, good for population density
# ─────────────────────────────────────────────────────────────

# FEATURE 1: Rainfall in last 24 hours (mm)
# Punjab normal rain: 0-30mm | heavy: 30-100mm | extreme: 100mm+
rainfall_24h_mm = np.where(
    seasons == 'dry',         np.random.exponential(scale=3,  size=N),
    np.where(
    seasons == 'pre_monsoon', np.random.exponential(scale=15, size=N),
    np.where(
    seasons == 'monsoon',     np.random.exponential(scale=45, size=N),
                              np.random.exponential(scale=12, size=N)  # post-monsoon
    ))
)
rainfall_24h_mm = np.clip(rainfall_24h_mm, 0, 200)


# FEATURE 2: River level normalized (0 = well below banks, 1 = at/above flood stage)
# Sutlej flood stage at Harike is ~6.5m. We normalize to 0-1 scale.
river_level_normalized = np.where(
    seasons == 'dry',         np.random.beta(a=1.5, b=8,   size=N),
    np.where(
    seasons == 'pre_monsoon', np.random.beta(a=2,   b=5,   size=N),
    np.where(
    seasons == 'monsoon',     np.random.beta(a=4,   b=3,   size=N),
                              np.random.beta(a=3,   b=4,   size=N)
    ))
)
river_level_normalized = np.clip(river_level_normalized, 0, 1)


# FEATURE 3: Elevation (meters)
# Punjab plains range: 150m (low near rivers) to 300m (Shivalik foothills)
# Lower elevation = more flood-prone. Using triangular distribution
# with mode at 185m (most of populated Punjab is in lowlands).
elevation_m = np.random.triangular(left=150, mode=185, right=300, size=N)


# FEATURE 4: Soil moisture (%)
# High soil moisture = ground is already saturated = water has nowhere to go
# = higher runoff = higher flood risk
soil_moisture_pct = np.where(
    seasons == 'dry',         np.random.uniform(5,  30, size=N),
    np.where(
    seasons == 'pre_monsoon', np.random.uniform(20, 55, size=N),
    np.where(
    seasons == 'monsoon',     np.random.uniform(55, 95, size=N),
                              np.random.uniform(40, 80, size=N)
    ))
)
soil_moisture_pct = np.clip(soil_moisture_pct, 0, 100)


# FEATURE 5: Days since last rain
# If ground is already wet from recent rain AND more rain comes → compound risk
days_since_rain = np.where(
    seasons == 'dry',         np.random.randint(5,  30, size=N),
    np.where(
    seasons == 'pre_monsoon', np.random.randint(2,  15, size=N),
    np.where(
    seasons == 'monsoon',     np.random.randint(0,  5,  size=N),
                              np.random.randint(1,  10, size=N)
    ))
).astype(float)


# FEATURE 6: Upstream zone severity (0-1)
# This is the CTDG cascade signal — if upstream zones (Harike barrage,
# Zira) are flooded, water flows downstream to Ferozepur, Moga, etc.
upstream_severity = np.where(
    seasons == 'monsoon',
    np.random.beta(a=2.5, b=3, size=N),
    np.random.beta(a=1,   b=5, size=N)
)
upstream_severity = np.clip(upstream_severity, 0, 1)


# FEATURE 7: Drainage quality (0=broken/non-existent, 1=excellent)
# Most rural Punjab drainage infrastructure is moderate quality.
# Using beta distribution skewed toward moderate (mean ~0.63)
drainage_quality = np.random.beta(a=5, b=3, size=N)
drainage_quality = np.clip(drainage_quality, 0, 1)


# FEATURE 8: Population density (people/km²)
# Punjab is one of India's most densely populated states.
# Using lognormal (right-skewed): some rural zones <200, some urban >3000
population_density = np.random.lognormal(mean=5.5, sigma=1.0, size=N)
population_density = np.clip(population_density, 50, 8000)


# FEATURE 9: Historical flood frequency (0-1)
# How often this zone floods during monsoon season historically.
# This is a stable zone characteristic, mostly low with some hotspots.
historical_flood_freq = np.random.beta(a=2, b=5, size=N)
historical_flood_freq = np.clip(historical_flood_freq, 0, 1)


# ─────────────────────────────────────────────────────────────
# STEP 3: Target variable — Flood Risk Score (0-1)
# ─────────────────────────────────────────────────────────────
# This is the number our model will learn to predict.
# It encodes real hydrology: which factors matter and how much.
#
# Weight breakdown (must sum to ~1.0):
#   Rainfall 24h:      0.25  ← primary trigger
#   River level:       0.25  ← primary trigger
#   Soil moisture:     0.15  ← compound amplifier
#   Upstream severity: 0.15  ← cascade signal
#   Elevation risk:    0.10  ← topographic vulnerability
#   Drainage failure:  0.10  ← infrastructure factor
#   History base:      0.15  ← long-term zone vulnerability

# Elevation risk: lower elevation = higher risk (normalized)
elevation_risk = 1 - (elevation_m - 150) / 150
elevation_risk = np.clip(elevation_risk, 0, 1)

# Recent rain factor: rain in last 7 days compounds soil saturation
recency_factor = np.maximum(0, 1 - days_since_rain / 7)

# Primary weighted score
flood_risk_score = (
    0.25 * (rainfall_24h_mm / 200) +
    0.25 * river_level_normalized +
    0.15 * (soil_moisture_pct / 100) +
    0.15 * upstream_severity +
    0.10 * elevation_risk +
    0.10 * (1 - drainage_quality)
)

# Blend in historical vulnerability (15% weight)
flood_risk_score = flood_risk_score * 0.85 + historical_flood_freq * 0.15

# Compound moisture × recency effect (small but realistic)
flood_risk_score += recency_factor * (soil_moisture_pct / 100) * 0.05

# Add realistic sensor/measurement noise
# Real data always has noise — this teaches the model not to overfit
noise = np.random.normal(loc=0, scale=0.025, size=N)
flood_risk_score = np.clip(flood_risk_score + noise, 0.0, 1.0)


# ─────────────────────────────────────────────────────────────
# STEP 4: Assemble and save
# ─────────────────────────────────────────────────────────────
df = pd.DataFrame({
    'rainfall_24h_mm':        np.round(rainfall_24h_mm, 2),
    'river_level_normalized': np.round(river_level_normalized, 4),
    'elevation_m':            np.round(elevation_m, 1),
    'soil_moisture_pct':      np.round(soil_moisture_pct, 1),
    'days_since_rain':        days_since_rain.astype(int),
    'upstream_severity':      np.round(upstream_severity, 4),
    'drainage_quality':       np.round(drainage_quality, 4),
    'population_density':     np.round(population_density, 0).astype(int),
    'historical_flood_freq':  np.round(historical_flood_freq, 4),
    'flood_risk_score':       np.round(flood_risk_score, 4),
    'season':                 seasons,  # kept for analysis only, dropped before training
})

os.makedirs('data', exist_ok=True)
df.to_csv('data/flood_training_data.csv', index=False)


# ─────────────────────────────────────────────────────────────
# STEP 5: Summary report
# ─────────────────────────────────────────────────────────────
print(f"\n✓ Dataset generated: {len(df):,} samples, {len(df.columns)} columns")
print(f"\nFeature summary:")
print(df.drop(columns=['season', 'flood_risk_score']).describe().round(2).to_string())

print(f"\nFlood risk score distribution:")
low      = (df.flood_risk_score < 0.3).sum()
moderate = ((df.flood_risk_score >= 0.3) & (df.flood_risk_score < 0.6)).sum()
high     = ((df.flood_risk_score >= 0.6) & (df.flood_risk_score < 0.8)).sum()
critical = (df.flood_risk_score >= 0.8).sum()
print(f"  LOW      (0.0–0.3): {low:>5,}  ({low/N*100:.1f}%)")
print(f"  MODERATE (0.3–0.6): {moderate:>5,}  ({moderate/N*100:.1f}%)")
print(f"  HIGH     (0.6–0.8): {high:>5,}  ({high/N*100:.1f}%)")
print(f"  CRITICAL (0.8–1.0): {critical:>5,}  ({critical/N*100:.1f}%)")

print(f"\nBy season:")
print(df.groupby('season')['flood_risk_score'].mean().round(3).to_string())

print(f"\n✓ Saved to: data/flood_training_data.csv")
print("\nNext step: run python train_model.py")
