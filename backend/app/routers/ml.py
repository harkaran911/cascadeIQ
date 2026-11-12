"""
CascadeIQ — ML Prediction Router
==================================
Endpoints:
  GET  /api/ml/info                → model metadata and training metrics
  GET  /api/ml/predict/{zone_id}  → ML flood risk for one zone
  GET  /api/ml/predict/all        → ML flood risk for every zone
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.zone import Zone, ZoneEdge
from app.services.ml_predictor import predict_zone_risk, predict_all_zones, get_model_info

router = APIRouter()


async def _compute_upstream_severity(zone_id: int, db: AsyncSession) -> float:
    """
    Look up all zones that have a directed edge INTO zone_id.
    Return mean severity_score of those upstream zones.
    This feeds the 'upstream_severity' feature the model was trained on.
    """
    result = await db.execute(
        select(ZoneEdge).where(ZoneEdge.to_zone_id == zone_id)
    )
    edges = result.scalars().all()

    if not edges:
        return 0.0

    upstream_ids = [e.from_zone_id for e in edges]
    result = await db.execute(
        select(Zone).where(Zone.id.in_(upstream_ids))
    )
    upstream_zones = result.scalars().all()

    if not upstream_zones:
        return 0.0

    return sum(z.severity_score or 0.0 for z in upstream_zones) / len(upstream_zones)


@router.get("/info")
async def ml_model_info():
    """Return model metadata, feature list, and training quality metrics."""
    try:
        return get_model_info()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/predict/all")
async def predict_all(db: AsyncSession = Depends(get_db)):
    """
    Run ML flood risk prediction for every zone.
    Uses current DB state (severity_score, vulnerability_index, etc.)
    plus graph-computed upstream_severity for each zone.
    """
    try:
        result = await db.execute(select(Zone))
        zones = result.scalars().all()

        # Compute upstream severity for every zone in one go
        graph_severity_map = {}
        for zone in zones:
            graph_severity_map[zone.id] = await _compute_upstream_severity(zone.id, db)

        predictions = predict_all_zones(zones, graph_severity_map)
        return {
            "count": len(predictions),
            "predictions": predictions,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/predict/{zone_id}")
async def predict_zone(zone_id: int, db: AsyncSession = Depends(get_db)):
    """
    Run ML flood risk prediction for a single zone.

    Returns the predicted score plus the feature vector used,
    so the frontend can show exactly what drove the prediction.
    """
    try:
        zone = await db.get(Zone, zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")

        upstream_severity = await _compute_upstream_severity(zone_id, db)
        result = predict_zone_risk(zone, upstream_severity=upstream_severity)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
