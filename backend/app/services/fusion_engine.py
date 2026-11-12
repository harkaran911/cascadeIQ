"""
Multi-Source Evidence Fusion Engine (MSEFE)
==========================================
Computes a Bayesian Incident Confidence Score (ICS) for each zone
by fusing reports from multiple sources with per-source trust weights.

Bayesian update rule (simplified):
  P(incident | evidence) ∝ ∏ P(evidence_i | incident) * P(incident)

In practice we use a weighted log-odds accumulator:
  log_odds_post = log_odds_prior + Σ trust_i * severity_i * direction_i

where direction_i = +1 (incident reported) or -1 (explicitly contradicted).

The posterior is then mapped back to [0,1] via sigmoid.

Evidence sources and their trust weights:
  AUTHORITY    0.95  (official government reports)
  IMD_WEATHER  0.85  (India Met Dept / OpenWeather)
  SATELLITE    0.80  (remote sensing)
  ML_MODEL     0.75  ← XGBoost flood risk predictor (CascadeIQ Phase 5)
  CITIZEN      0.40  (crowdsourced reports)
  SOCIAL_MEDIA 0.25  (NLP-extracted social media)
"""
import math
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.incident import Incident, SOURCE_TRUST
from app.models.zone import Zone


# Prior: uninformed — slight lean toward no-incident
PRIOR_LOG_ODDS = math.log(0.15 / 0.85)  # ~= -1.73

# Evidence decays over time — half-life 6 hours
EVIDENCE_HALF_LIFE_H = 6.0

# Corroboration bonus: each additional source confirming bumps the weight
CORROBORATION_BONUS = 0.10


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _time_decay(created_at: datetime) -> float:
    """Returns a decay factor ∈ (0,1] based on incident age."""
    age_h = (datetime.utcnow() - created_at).total_seconds() / 3600.0
    return math.exp(-0.693 * age_h / EVIDENCE_HALF_LIFE_H)  # 0.693 = ln(2)


ML_EVIDENCE_TRUST = 0.75   # XGBoost model trust weight in the fusion


async def update_zone_confidence(
    zone_id: int,
    db: AsyncSession,
    ml_flood_risk: Optional[float] = None,
) -> float:
    """
    Recompute the incident_confidence for a zone by fusing all
    recent incidents (last 24 h) plus an optional ML model prediction.

    Parameters
    ----------
    zone_id
        Primary key of the zone to recompute.
    db
        Async DB session.
    ml_flood_risk
        XGBoost flood risk prediction (0–1). If provided, it is fused
        into the log-odds accumulator with trust weight 0.75, sitting
        between satellite imagery (0.80) and citizen reports (0.40).
        If None, only incident reports are used (backward-compatible).

    Returns
    -------
    float
        Updated incident_confidence in [0, 1].
    """
    cutoff = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(Incident).where(
            Incident.zone_id == zone_id,
            Incident.created_at >= cutoff,
        )
    )
    incidents = result.scalars().all()

    log_odds = PRIOR_LOG_ODDS

    # ── Evidence stream 1: Incident reports (all sources) ─────────────────────
    for inc in incidents:
        decay = _time_decay(inc.created_at)
        trust = SOURCE_TRUST.get(inc.source, 0.4)
        corroboration_multiplier = 1.0 + CORROBORATION_BONUS * max(0, inc.corroboration_count - 1)
        weight = trust * decay * corroboration_multiplier
        log_odds += weight * inc.severity * 3.0   # scaling factor for meaningful shift

    # ── Evidence stream 2: ML model prediction (trust_weight = 0.75) ─────────
    # The XGBoost model runs on tabular zone features (rainfall, river level,
    # soil moisture, upstream severity, elevation, drainage quality, etc.).
    # It acts as a persistent background evidence signal — unlike incident reports
    # which may be absent or delayed, the model always has an opinion.
    if ml_flood_risk is not None:
        ml_weight = ML_EVIDENCE_TRUST
        log_odds += ml_weight * float(ml_flood_risk) * 3.0

    confidence = _sigmoid(log_odds)

    # ── Heuristic: silence from an isolated zone is suspicious ────────────────
    zone = await db.get(Zone, zone_id)
    if zone and zone.is_isolated and len(incidents) == 0 and ml_flood_risk is None:
        confidence = max(confidence, 0.45)

    if zone:
        zone.incident_confidence = round(confidence, 4)
        db.add(zone)
        await db.commit()

    return confidence


async def recompute_all_zones(
    db: AsyncSession,
    ml_risk_map: Optional[dict] = None,
) -> dict:
    """
    Recompute MSEFE confidence for every zone.
    Called periodically or after cascade tick.

    Parameters
    ----------
    ml_risk_map
        Optional {zone_id: ml_flood_risk} from the ML predictor.
        If provided, each zone's ML prediction is fused into its confidence.
    """
    result = await db.execute(select(Zone))
    zones = result.scalars().all()
    updates = {}
    ml = ml_risk_map or {}
    for zone in zones:
        ml_risk = ml.get(zone.id)
        conf = await update_zone_confidence(zone.id, db, ml_flood_risk=ml_risk)
        updates[zone.id] = conf
    return updates
