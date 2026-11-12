"""
CascadeIQ — Phase 3+4: EDA + Model Training
=============================================
Loads the generated dataset, runs exploratory data analysis,
trains an XGBoost regressor, evaluates it, and saves the model.

Run AFTER generate_dataset.py:
  python train_model.py

Output:
  model/flood_risk_model.pkl    ← trained model (loaded by backend)
  model/feature_names.json      ← input feature order (critical for inference)
  model/model_metrics.json      ← saved evaluation results
  outputs/                      ← EDA and training plots (PNG files)
"""

import json
import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import joblib

from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.inspection import permutation_importance

os.makedirs('model', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

print("=" * 60)
print("CascadeIQ — EDA + Model Training")
print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# PHASE 3: EXPLORATORY DATA ANALYSIS (EDA)
# ═══════════════════════════════════════════════════════════════
# EDA = looking at your data before training anything.
# Purpose: catch problems early, understand distributions,
#          see which features actually correlate with the target.
# ═══════════════════════════════════════════════════════════════

print("\n── Phase 3: Exploratory Data Analysis ──\n")

# Load data
df = pd.read_csv('data/flood_training_data.csv')
print(f"Loaded {len(df):,} samples with {len(df.columns)} columns")

# Define our features (X) and target (y)
# 'season' is dropped — it's a string category we used only for generation
FEATURES = [
    'rainfall_24h_mm',
    'river_level_normalized',
    'elevation_m',
    'soil_moisture_pct',
    'days_since_rain',
    'upstream_severity',
    'drainage_quality',
    'population_density',
    'historical_flood_freq',
]
TARGET = 'flood_risk_score'

X = df[FEATURES]
y = df[TARGET]

print(f"\nFeatures ({len(FEATURES)}): {FEATURES}")
print(f"Target: {TARGET}")

# Basic stats
print("\nTarget statistics:")
print(f"  Mean:   {y.mean():.4f}")
print(f"  Std:    {y.std():.4f}")
print(f"  Min:    {y.min():.4f}")
print(f"  Max:    {y.max():.4f}")
print(f"  Median: {y.median():.4f}")


# ── EDA Plot 1: Feature Distributions ──────────────────────────
print("\nGenerating EDA plots...")

fig, axes = plt.subplots(3, 3, figsize=(15, 12))
fig.suptitle('CascadeIQ — Feature Distributions', fontsize=16, fontweight='bold', y=0.98)

for i, feature in enumerate(FEATURES):
    ax = axes[i // 3][i % 3]
    ax.hist(X[feature], bins=50, color='#2563eb', alpha=0.75, edgecolor='white', linewidth=0.3)
    ax.set_title(feature, fontsize=10, fontweight='bold')
    ax.set_xlabel('Value')
    ax.set_ylabel('Count')
    ax.grid(True, alpha=0.3)
    # Add mean line
    ax.axvline(X[feature].mean(), color='red', linestyle='--', linewidth=1.5,
               label=f'mean={X[feature].mean():.2f}')
    ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('outputs/01_feature_distributions.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/01_feature_distributions.png")


# ── EDA Plot 2: Target Distribution ────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('CascadeIQ — Flood Risk Score Distribution', fontsize=14, fontweight='bold')

# Histogram
axes[0].hist(y, bins=60, color='#dc2626', alpha=0.75, edgecolor='white', linewidth=0.3)
axes[0].set_xlabel('Flood Risk Score (0=safe, 1=critical)')
axes[0].set_ylabel('Count')
axes[0].set_title('Distribution of Target Variable')
axes[0].axvline(0.3, color='orange', linestyle='--', linewidth=1.5, label='LOW threshold (0.3)')
axes[0].axvline(0.6, color='red', linestyle='--', linewidth=1.5, label='HIGH threshold (0.6)')
axes[0].axvline(0.8, color='darkred', linestyle='--', linewidth=1.5, label='CRITICAL threshold (0.8)')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# By season
season_means = df.groupby('season')[TARGET].mean().sort_values()
colors = ['#3b82f6', '#f97316', '#10b981', '#6366f1']
bars = axes[1].bar(season_means.index, season_means.values, color=colors, alpha=0.85, edgecolor='white')
axes[1].set_xlabel('Season')
axes[1].set_ylabel('Mean Flood Risk Score')
axes[1].set_title('Mean Risk by Season')
axes[1].set_ylim(0, 1)
axes[1].grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, season_means.values):
    axes[1].text(bar.get_x() + bar.get_width()/2, val + 0.01,
                 f'{val:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('outputs/02_target_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/02_target_distribution.png")


# ── EDA Plot 3: Correlation Matrix ─────────────────────────────
# Correlation = how linearly related two variables are.
# Values range -1 to +1.
# +1 = as X goes up, Y goes up perfectly
# -1 = as X goes up, Y goes down perfectly
#  0 = no linear relationship
#
# This tells us which features are most predictive of flood risk.

corr_data = df[FEATURES + [TARGET]].corr()

fig, ax = plt.subplots(figsize=(12, 10))
mask = np.triu(np.ones_like(corr_data, dtype=bool))  # hide upper triangle (it's a mirror)
sns.heatmap(
    corr_data,
    mask=mask,
    annot=True,
    fmt='.2f',
    cmap='RdBu_r',
    center=0,
    vmin=-1, vmax=1,
    ax=ax,
    linewidths=0.5,
    annot_kws={'size': 9}
)
ax.set_title('CascadeIQ — Feature Correlation Matrix\n(last row = correlation with flood_risk_score)',
             fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('outputs/03_correlation_matrix.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/03_correlation_matrix.png")

# Print top correlations with target (most important)
target_corr = corr_data[TARGET].drop(TARGET).sort_values(key=abs, ascending=False)
print(f"\nFeature correlations with {TARGET} (sorted by strength):")
for feat, val in target_corr.items():
    direction = "↑" if val > 0 else "↓"
    bar = "█" * int(abs(val) * 20)
    print(f"  {feat:<30} {direction} {val:+.4f}  {bar}")


# ── EDA Plot 4: Scatter plots (top 4 features vs target) ───────
top_features = target_corr.head(4).index.tolist()

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('CascadeIQ — Top 4 Features vs Flood Risk Score', fontsize=14, fontweight='bold')

for i, feat in enumerate(top_features):
    ax = axes[i // 2][i % 2]
    # Sample 2000 points for speed (plotting all 10k is slow)
    sample = df.sample(2000, random_state=42)
    scatter = ax.scatter(
        sample[feat], sample[TARGET],
        c=sample[TARGET], cmap='RdYlGn_r',
        alpha=0.4, s=15, edgecolors='none'
    )
    # Trend line
    z = np.polyfit(sample[feat], sample[TARGET], 1)
    p = np.poly1d(z)
    x_line = np.linspace(sample[feat].min(), sample[feat].max(), 100)
    ax.plot(x_line, p(x_line), 'k--', linewidth=2, alpha=0.8, label=f'trend (r={target_corr[feat]:.2f})')
    ax.set_xlabel(feat)
    ax.set_ylabel('flood_risk_score')
    ax.set_title(f'{feat}', fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)
    plt.colorbar(scatter, ax=ax, label='risk score')

plt.tight_layout()
plt.savefig('outputs/04_scatter_plots.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/04_scatter_plots.png")

print("\n✓ EDA complete — check the outputs/ folder for plots")


# ═══════════════════════════════════════════════════════════════
# PHASE 4: MODEL TRAINING
# ═══════════════════════════════════════════════════════════════
# XGBoost (eXtreme Gradient Boosting)
#
# How it works in plain English:
# 1. Build a simple decision tree → it makes predictions but has errors
# 2. Build ANOTHER tree that focuses on where the first tree was wrong
# 3. Add that tree to the ensemble (correction on top of correction)
# 4. Repeat 500-1000 times
# 5. Final prediction = sum of all tree predictions
#
# This is called "boosting" — many weak learners → one strong learner.
# XGBoost dominates tabular data competitions because it's fast,
# handles missing values, and doesn't need feature scaling.
# ═══════════════════════════════════════════════════════════════

print("\n── Phase 4: Model Training ──\n")

# ── Train / Test Split ──────────────────────────────────────────
# We hold out 20% of data as a "test set" that the model NEVER sees
# during training. We use this to honestly evaluate performance.
# The model only trains on the 80% "train set".
#
# random_state=42 ensures the same split every time you run this.

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

print(f"Training set:  {len(X_train):,} samples")
print(f"Test set:      {len(X_test):,} samples")

# ── Hyperparameters Explained ───────────────────────────────────
# n_estimators=800      → build 800 trees (more = better, until diminishing returns)
# max_depth=6           → each tree can be at most 6 levels deep (prevents overfitting)
# learning_rate=0.05    → each tree contributes only 5% to final answer (slow & steady)
# subsample=0.8         → each tree sees random 80% of training data (prevents overfitting)
# colsample_bytree=0.8  → each tree sees random 80% of features (prevents overfitting)
# min_child_weight=3    → leaf nodes need ≥3 samples (prevents overfitting on noise)
# reg_alpha=0.1         → L1 regularization (punishes complex models)
# reg_lambda=1.0        → L2 regularization (punishes large weights)
# random_state=42       → reproducibility

model = XGBRegressor(
    n_estimators=800,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective='reg:squarederror',  # minimize squared error (standard for regression)
    n_jobs=-1,                      # use all CPU cores
    random_state=42,
    verbosity=0
)

print("\nTraining XGBoost model...")
print("(800 trees × 8,000 training samples — should take 10-30 seconds)\n")

model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    verbose=100  # print progress every 100 trees
)

print("\n✓ Training complete!")


# ── Evaluation Metrics ──────────────────────────────────────────
# MAE  (Mean Absolute Error)   → average prediction error in same units as target
#                                 e.g. MAE=0.05 means predictions are off by 0.05 on a 0-1 scale
# RMSE (Root Mean Squared Error) → like MAE but penalizes large errors more
# R²   (R-squared)             → what % of variance in the target the model explains
#                                 R²=0.95 means model explains 95% of variation → excellent
#                                 R²=0.0 means model is as good as predicting the mean

y_pred_train = model.predict(X_train)
y_pred_test  = model.predict(X_test)

train_mae  = mean_absolute_error(y_train, y_pred_train)
test_mae   = mean_absolute_error(y_test,  y_pred_test)
train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse  = np.sqrt(mean_squared_error(y_test,  y_pred_test))
train_r2   = r2_score(y_train, y_pred_train)
test_r2    = r2_score(y_test,  y_pred_test)

print(f"\n{'Metric':<12} {'Train':>10} {'Test':>10}  {'Notes'}")
print("-" * 55)
print(f"{'MAE':<12} {train_mae:>10.4f} {test_mae:>10.4f}  (lower = better, 0 = perfect)")
print(f"{'RMSE':<12} {train_rmse:>10.4f} {test_rmse:>10.4f}  (lower = better, 0 = perfect)")
print(f"{'R²':<12} {train_r2:>10.4f} {test_r2:>10.4f}  (higher = better, 1 = perfect)")

# Overfitting check:
# If train metrics are WAY better than test metrics → model memorized training data
# Small gap = good generalization
gap = train_r2 - test_r2
print(f"\nOverfit check (train R² - test R²): {gap:.4f}")
if gap < 0.02:
    print("  → Excellent generalization, no overfitting detected")
elif gap < 0.05:
    print("  → Good generalization, minor overfitting (acceptable)")
else:
    print("  → Possible overfitting — consider reducing n_estimators or max_depth")

# 5-fold cross-validation (optional but thorough)
# Splits data into 5 chunks, trains on 4, tests on 1, rotates — gives 5 R² scores
print("\nRunning 5-fold cross-validation (may take 30s)...")
cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2', n_jobs=-1)
print(f"CV R² scores: {[f'{s:.4f}' for s in cv_scores]}")
print(f"Mean CV R²:   {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")


# ── Training Curve Plot ─────────────────────────────────────────
print("\nGenerating training + evaluation plots...")

results = model.evals_result()
train_errors = results['validation_0']['rmse']
test_errors  = results['validation_1']['rmse']

fig, ax = plt.subplots(figsize=(12, 5))
epochs = range(len(train_errors))
ax.plot(epochs, train_errors, label='Training RMSE',   color='#3b82f6', linewidth=1.5)
ax.plot(epochs, test_errors,  label='Test RMSE',       color='#ef4444', linewidth=1.5)
ax.set_xlabel('Number of Trees (Boosting Rounds)')
ax.set_ylabel('RMSE')
ax.set_title('CascadeIQ — Training Curve\n(RMSE should decrease and stabilize for both train and test)',
             fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_xlim(0, len(train_errors))
plt.tight_layout()
plt.savefig('outputs/05_training_curve.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/05_training_curve.png")


# ── Actual vs Predicted Plot ────────────────────────────────────
# If the model is good, predictions should line up along y=x (diagonal)
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('CascadeIQ — Model Evaluation', fontsize=14, fontweight='bold')

# Scatter: actual vs predicted
axes[0].scatter(y_test, y_pred_test, alpha=0.3, s=10, color='#3b82f6', edgecolors='none')
axes[0].plot([0, 1], [0, 1], 'r--', linewidth=2, label='Perfect prediction')
axes[0].set_xlabel('Actual Flood Risk Score')
axes[0].set_ylabel('Predicted Flood Risk Score')
axes[0].set_title(f'Actual vs Predicted\nTest R² = {test_r2:.4f}, MAE = {test_mae:.4f}')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].set_xlim(0, 1)
axes[0].set_ylim(0, 1)

# Residual plot: how wrong we are, and where
residuals = y_test.values - y_pred_test
axes[1].scatter(y_pred_test, residuals, alpha=0.3, s=10, color='#f59e0b', edgecolors='none')
axes[1].axhline(y=0, color='red', linestyle='--', linewidth=2)
axes[1].set_xlabel('Predicted Flood Risk Score')
axes[1].set_ylabel('Residual (Actual − Predicted)')
axes[1].set_title('Residual Plot\n(should be scattered randomly around 0)')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/06_actual_vs_predicted.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/06_actual_vs_predicted.png")


# ── Feature Importance ──────────────────────────────────────────
# XGBoost tracks which features it used most when building trees.
# Higher importance = that feature was more useful for reducing prediction error.
# This is powerful for interpretability — you can explain to anyone
# WHICH factors are driving flood risk predictions.

importance_scores = model.feature_importances_
importance_df = pd.DataFrame({
    'feature': FEATURES,
    'importance': importance_scores
}).sort_values('importance', ascending=True)

fig, ax = plt.subplots(figsize=(10, 7))
colors = ['#ef4444' if imp > 0.15 else '#3b82f6' if imp > 0.08 else '#94a3b8'
          for imp in importance_df.importance]
bars = ax.barh(importance_df.feature, importance_df.importance,
               color=colors, edgecolor='white', height=0.7)
ax.set_xlabel('Feature Importance (Gain)', fontsize=12)
ax.set_title('CascadeIQ — What drives flood risk predictions?\n(XGBoost Feature Importance)',
             fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3, axis='x')

for bar, val in zip(bars, importance_df.importance):
    ax.text(val + 0.001, bar.get_y() + bar.get_height()/2,
            f'{val:.4f}', va='center', fontsize=10)

plt.tight_layout()
plt.savefig('outputs/07_feature_importance.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ outputs/07_feature_importance.png")

print("\nFeature importance ranking:")
importance_sorted = importance_df.sort_values('importance', ascending=False)
for i, (_, row) in enumerate(importance_sorted.iterrows()):
    bar = "█" * int(row.importance * 100)
    print(f"  #{i+1:>2}  {row.feature:<30} {row.importance:.4f}  {bar}")


# ═══════════════════════════════════════════════════════════════
# SAVE MODEL AND METADATA
# ═══════════════════════════════════════════════════════════════

# Save model
model_path = 'model/flood_risk_model.pkl'
joblib.dump(model, model_path)
print(f"\n✓ Model saved: {model_path}")

# Save feature names (CRITICAL — inference must use exact same feature order)
feature_path = 'model/feature_names.json'
with open(feature_path, 'w') as f:
    json.dump(FEATURES, f, indent=2)
print(f"✓ Feature names saved: {feature_path}")

# Save metrics for the backend to serve via API
metrics = {
    'test_mae':      round(float(test_mae), 6),
    'test_rmse':     round(float(test_rmse), 6),
    'test_r2':       round(float(test_r2), 6),
    'train_r2':      round(float(train_r2), 6),
    'cv_r2_mean':    round(float(cv_scores.mean()), 6),
    'cv_r2_std':     round(float(cv_scores.std()), 6),
    'n_training':    len(X_train),
    'n_test':        len(X_test),
    'n_features':    len(FEATURES),
    'n_estimators':  800,
}
metrics_path = 'model/model_metrics.json'
with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)
print(f"✓ Metrics saved: {metrics_path}")


# ═══════════════════════════════════════════════════════════════
# QUICK SANITY CHECK
# ═══════════════════════════════════════════════════════════════
# Reload model and run a manual prediction to confirm it works.
# This is what the backend service will do at inference time.

print("\n── Sanity Check: Manual Prediction ──")
loaded_model = joblib.load(model_path)
with open(feature_path) as f:
    loaded_features = json.load(f)

# Scenario 1: Heavy monsoon flood (should be HIGH risk)
scenario_flood = pd.DataFrame([{
    'rainfall_24h_mm':        145.0,   # heavy rainfall
    'river_level_normalized':   0.85,  # river near flood stage
    'elevation_m':            162.0,   # low elevation (Harike area)
    'soil_moisture_pct':       88.0,   # very saturated
    'days_since_rain':            1,   # just rained yesterday too
    'upstream_severity':        0.78,  # Harike barrage is flooded
    'drainage_quality':         0.35,  # poor drainage
    'population_density':      1200,   # medium-high population
    'historical_flood_freq':    0.72,  # frequently floods
}], columns=loaded_features)

pred_flood = loaded_model.predict(scenario_flood)[0]
print(f"\nScenario 1 (Heavy monsoon flood conditions):")
print(f"  Predicted risk: {pred_flood:.4f}  → {'CRITICAL' if pred_flood >= 0.8 else 'HIGH' if pred_flood >= 0.6 else 'MODERATE'}")

# Scenario 2: Dry season (should be LOW risk)
scenario_dry = pd.DataFrame([{
    'rainfall_24h_mm':          2.0,   # almost no rain
    'river_level_normalized':   0.12,  # river very low
    'elevation_m':            245.0,   # higher elevation
    'soil_moisture_pct':       12.0,   # dry soil
    'days_since_rain':           18,   # no rain for weeks
    'upstream_severity':        0.05,  # upstream zones fine
    'drainage_quality':         0.80,  # decent drainage
    'population_density':       350,   # low population area
    'historical_flood_freq':    0.08,  # rarely floods
}], columns=loaded_features)

pred_dry = loaded_model.predict(scenario_dry)[0]
print(f"\nScenario 2 (Dry season, no flood risk):")
print(f"  Predicted risk: {pred_dry:.4f}  → {'LOW' if pred_dry < 0.3 else 'MODERATE'}")

print("\n" + "=" * 60)
print("✓ Training complete!")
print(f"  Test R²: {test_r2:.4f}  (explained variance)")
print(f"  Test MAE: {test_mae:.4f} (avg prediction error on 0-1 scale)")
print(f"  Model: model/flood_risk_model.pkl")
print("=" * 60)
print("\nNext step: integrate the model into the CascadeIQ backend")
print("(We'll do that together in Phase 5)")
