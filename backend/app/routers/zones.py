from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.zone import Zone, ZoneEdge

router = APIRouter()


@router.get("/")
async def list_zones(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zone))
    zones = result.scalars().all()
    return [
        {
            "id": z.id, "name": z.name, "district": z.district,
            "lat": z.lat, "lon": z.lon,
            "population": z.population,
            "vulnerability_index": z.vulnerability_index,
            "elevation_m": z.elevation_m,
            "has_hospital": z.has_hospital,
            "has_shelter": z.has_shelter,
            "severity_score": z.severity_score,
            "flood_depth_m": z.flood_depth_m,
            "time_to_critical_h": z.time_to_critical_h,
            "is_isolated": z.is_isolated,
            "incident_confidence": z.incident_confidence,
            "updated_at": z.updated_at,
        }
        for z in zones
    ]


@router.get("/{zone_id}")
async def get_zone(zone_id: int, db: AsyncSession = Depends(get_db)):
    z = await db.get(Zone, zone_id)
    if not z:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Zone not found")
    return z


@router.get("/{zone_id}/edges")
async def zone_edges(zone_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ZoneEdge).where(
            (ZoneEdge.from_zone_id == zone_id) | (ZoneEdge.to_zone_id == zone_id)
        )
    )
    edges = result.scalars().all()
    return [
        {
            "id": e.id,
            "from_zone_id": e.from_zone_id, "to_zone_id": e.to_zone_id,
            "edge_type": e.edge_type, "passable": e.passable,
            "degradation_factor": e.degradation_factor,
            "travel_time_min": e.travel_time_min,
        }
        for e in edges
    ]
