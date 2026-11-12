"""
CascadeIQ — ML Flood Risk Predictor
=====================================
Loads the trained XGBoost model and runs inference on zone data.

The model was trained on 9 features derived from hydrology + zone state.
At inference time we map the zone's known database fields to those features,
filling gaps with smart proxies based on domain knowledge.

Trust weight fed into MSEFE: 0.75
  (between satellite imagery 0.80 and citizen report 0.40)
"""
import json
import os
import math
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger(__name__)

# ── Model loading ─────────────────────────────────────────────────────────────
_MODEL_DIR  = Path(__file__).parent.parent.parent / "ml_model"
_MODEL_PATH = _MODEL_DIR / "flood_risk_model.pkl"
_FEAT_PATH  = _MODEL_DIR / "feature_names.json"
_METRICS_PATH = _MODEL_DIR / "model_metrics.json"

# Singleton — loaded once at first call, reused every request
_model = None
_feature_names: list[str] = []
_metrics: dict = {}


def _load_model():
    global _model, _feature_names, _metrics
    if _model is not None:
        return  # already loaded

    if not _MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at {_MODEL_PATH}. "
            "Run ml/generate_dataset.py then ml/train_model.py first."
        )

    logger.info(f"Loading XGBoost flood risk model from {_MODEL_PATH}")
    _model = joblib.load(_MODEL_PATH)

    with open(_FEAT_PATH) as f:
        _feature_names = json.load(f)

    if _METRICS_PATH.exists():
        with open(_METRICS_PATH) as f:
            _metrics = json.load(f)

    logger.info(f"Model loaded — R²={_metrics.get('test_r2', '?')}, "
                f"MAE={_metrics.get('test_mae', '?')}, "
                f"features={_feature_names}")


# ── Feature construction ───────────────────────────────────────────────────────
def _build_feature_vector(
    zone,
    upstream_severity: float = 0.0,
    rainfall_24h_mm: Optional[float] = None,
) -> dict:
    """
    Map CascadeIQ zone fields → XGBoost feature vector.

    Parameters
    ----------
    zone
        SQLAlchemy Zone ORM object (or any object with the right attributes)
    upstream_severity
        Mean severity of upstream-connected zones (computed by the router
        from the CTDG; defaults to 0.0 when no upstream zones exist)
    rainfall_24h_mm
        If we have a live weather reading, pass it here.
        Otherwise derived from severity.

    Returns
    -------
    dict mapping feature_name → float, in the exact order the model expects
    """
    sev = float(zone.severity_score or 0.0)
    vuln = float(zone.vulnerability_index or 0.5)
    elev = float(zone.elevation_m or 200.0)
    pop = float(zone.population or 1000)

    # ── rainfall_24h_mm ───────────────────────────────────────────────────────
    # If live weather reading provided → use it.
    # Otherwise estimate: a zone at severity 0.9 is in ~100-120 mm/day territory.
    if rainfall_24h_mm is not None:
        rain = float(rainfall_24h_mm)
    else:
        # Exponential mapping: sev 0 → ~0 mm, sev 0.5 → ~25 mm, sev 0.9 → ~90 mm
        rain = min(200.0, (math.exp(sev * 3.5) - 1) * 4.5)

    # ── river_level_normalized ────────────────────────────────────────────────
    # severity_score IS essentially a river level proxy for riverside zones
    river_level = sev

    # ── soil_moisture_pct ─────────────────────────────────────────────────────
    # High severity + recent flood → saturated soil.
    # We approximate: severity drives base, flood_depth amplifies.
    flood_depth = float(zone.flood_depth_m or 0.0)
    soil_moisture = min(100.0, sev * 65.0 + flood_depth * 8.0 + 15.0)

    # ── days_since_rain ───────────────────────────────────────────────────────
    # High severity means it rained recently. Inverse mapping.
    # sev 0.9 → 0-1 days, sev 0.3 → ~8 days, sev 0.0 → 20+ days
    days_since_rain = max(0.0, (1.0 - sev) ** 1.5 * 22.0)

    # ── upstream_severity (passed in from graph engine) ───────────────────────
    up_sev = float(upstream_severity)

    # ── drainage_quality ─────────────────────────────────────────────────────
    # Inverse of vulnerability: more vulnerable zone → worse drainage
    drainage_quality = max(0.05, 1.0 - vuln * 0.9)

    # ── population_density (people/km²) ──────────────────────────────────────
    # We don't have zone area, so approximate from raw population.
    # Punjab zones range 50–8000 people/km². Use log-scaled estimate.
    pop_density = min(8000.0, max(50.0, pop / 50.0))

    # ── historical_flood_freq ─────────────────────────────────────────────────
    # vulnerability_index is the best available proxy.
    hist_freq = min(1.0, vuln * 0.9)

    return {
        "rainfall_24h_mm":        round(rain, 2),
        "river_level_normalized": round(river_level, 4),
        "elevation_m":            round(elev, 1),
        "soil_moisture_pct":      round(soil_moisture, 1),
        "days_since_rain":        round(days_since_rain, 1),
        "upstream_severity":      round(up_sev, 4),
        "drainage_quality":       round(drainage_quality, 4),
        "population_density":     round(pop_density, 0),
        "historical_flood_freq":  round(hist_freq, 4),
    }


# ── Public API ─────────────────────────────────────────────────────────────────
ML_TRUST_WEIGHT = 0.75  # used by MSEFE when fusing this prediction


def predict_zone_risk(
    zone,
    upstream_severity: float = 0.0,
    rainfall_24h_mm: Optional[float] = None,
) -> dict:
    """
    Run ML flood risk prediction for a single zone.

    Returns
    -------
    {
        "zone_id": int,
        "ml_flood_risk": float,       ← 0–1 prediction
        "risk_label": str,            ← LOW / MODERATE / HIGH / CRITICAL
        "trust_weight": float,        ← 0.75 (for MSEFE)
        "features_used": dict,        ← the feature vector (for transparency)
        "model_r2": float,            ← model quality reference
    }
    """
    _load_model()

    features = _build_feature_vector(zone, upstream_severity, rainfall_24h_mm)

    # Build DataFrame in EXACT feature order the model was trained on
    X = pd.DataFrame([features], columns=_feature_names)
    prediction = float(_model.predict(X)[0])
    prediction = max(0.0, min(1.0, prediction))  # clamp to [0,1]

    if prediction >= 0.8:
        label = "CRITICAL"
    elif prediction >= 0.6:
        label = "HIGH"
    elif prediction >= 0.3:
        label = "MODERATE"
    else:
        label = "LOW"

    return {
        "zone_id": zone.id,
        "ml_flood_risk": round(prediction, 4),
        "risk_label": label,
        "trust_weight": ML_TRUST_WEIGHT,
        "features_used": features,
        "model_r2": _metrics.get("test_r2"),
    }


def predict_all_zones(zones: list, graph_severity_map: dict = None) -> list[dict]:
    """
    Run ML predictions for every zone.

    Parameters
    ----------
    zones
        List of Zone ORM objects
    graph_severity_map
        Optional {zone_id: upstream_severity} computed from the CTDG.
        If None, upstream_severity defaults to 0.0 for all zones.
    """
    _load_model()

    results = []
    gsm = graph_severity_map or {}

    for zone in zones:
        up_sev = gsm.get(zone.id, 0.0)
        result = predict_zone_risk(zone, upstream_severity=up_sev)
        results.append(result)

    return results


def get_model_info() -> dict:
    """Return model metadata — used by the /api/ml/info endpoint."""
    _load_model()
    return {
        "model_type": "XGBoost Regressor",
        "task": "Flood risk score regression (0–1)",
        "features": _feature_names,
        "trust_weight_in_msefe": ML_TRUST_WEIGHT,
        "metrics": _metrics,
        "model_path": str(_MODEL_PATH),
    }
