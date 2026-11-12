"""
Optimizer router — runs the PRO (Predictive Resource Optimizer) on demand
and returns a ranked list of deployment directives.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.zone import Zone
from app.models.resource import Resource, Deployment

router = APIRouter()


@router.post("/run")
async def run_optimizer(db: AsyncSession = Depends(get_db)):
    """Trigger a fresh optimizer run. Returns deployment directives."""
    from app.services.optimizer import run_optimization
    directives = await run_optimization(db)
    return {"directives": directives, "count": len(directives)}


@router.get("/directives")
async def get_directives(db: AsyncSession = Depends(get_db)):
    """Return current pending optimizer directives sorted by priority."""
    result = await db.execute(
        select(Deployment).order_by(Deployment.priority_rank)
    )
    deps = result.scalars().all()
    return [
        {
            "id": d.id,
            "resource_id": d.resource_id,
            "from_zone_id": d.from_zone_id,
            "to_zone_id": d.to_zone_id,
            "status": d.status,
            "priority_rank": d.priority_rank,
            "urgency_score": d.urgency_score,
            "rationale": d.rationale,
            "estimated_travel_min": d.estimated_travel_min,
            "deadline_minutes": d.deadline_minutes,
        }
        for d in deps
    ]


@router.get("/cascade")
async def get_cascade_state(db: AsyncSession = Depends(get_db)):
    """Return the current cascade graph state — node risk scores and edge states."""
    from app.services.graph_engine import get_cascade_snapshot
    snapshot = await get_cascade_snapshot(db)
    return snapshot


@router.post("/tick")
async def cascade_tick(ticks: int = 1, db: AsyncSession = Depends(get_db)):
    """
    Advance the cascade simulation by `ticks` propagation steps.
    Useful for demo: call /api/optimizer/tick to watch flood spread in real time.
    """
    from app.services.graph_engine import propagate_cascade
    from app.services.fusion_engine import recompute_all_zones
    result = await propagate_cascade(db, ticks=ticks)
    confidence_map = await recompute_all_zones(db)
    return {
        "cascade_result": result,
        "zones_with_confidence_updated": len(confidence_map),
    }
