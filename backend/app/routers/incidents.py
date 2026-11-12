from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.models.incident import Incident, IncidentSource, IncidentType, SOURCE_TRUST

router = APIRouter()


class IncidentCreate(BaseModel):
    zone_id: int
    source: IncidentSource = IncidentSource.CITIZEN
    incident_type: IncidentType
    severity: float = 0.5
    description: str | None = None
    reporter_name: str | None = None
    reporter_contact: str | None = None


@router.get("/")
async def list_incidents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).order_by(Incident.created_at.desc()))
    return result.scalars().all()


@router.post("/", status_code=201)
async def create_incident(payload: IncidentCreate, db: AsyncSession = Depends(get_db)):
    trust = SOURCE_TRUST.get(payload.source, 0.4)
    incident = Incident(
        zone_id=payload.zone_id,
        source=payload.source,
        incident_type=payload.incident_type,
        severity=payload.severity,
        description=payload.description,
        reporter_name=payload.reporter_name,
        reporter_contact=payload.reporter_contact,
        trust_weight=trust,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    # ── AI classification via Groq (non-blocking — failure doesn't affect response) ──
    ai_result = None
    if payload.description:
        try:
            from app.services.incident_classifier import classify_incident
            ai_result = await classify_incident(payload.description)
            if ai_result:
                import json as _json
                incident.ai_incident_type = ai_result["incident_type"]
                incident.ai_severity      = ai_result["severity"]
                incident.ai_confidence    = ai_result["confidence"]
                incident.ai_keywords      = _json.dumps(ai_result["keywords"])
                incident.ai_reasoning     = ai_result["reasoning"]
                await db.commit()
        except Exception as _e:
            pass  # Groq down — incident still saved, just no AI tag

    # Trigger MSEFE zone confidence update
    from app.services.fusion_engine import update_zone_confidence
    await update_zone_confidence(payload.zone_id, db)

    return {
        "id":           incident.id,
        "trust_weight": trust,
        "message":      "Incident logged",
        "ai_classification": ai_result,   # None if Groq unavailable
    }
