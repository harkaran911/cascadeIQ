from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.models.resource import Resource, ResourceType, ResourceStatus, Deployment, DeploymentStatus

router = APIRouter()


class ResourceCreate(BaseModel):
    name: str
    resource_type: ResourceType
    quantity: int = 1
    zone_id: int | None = None
    capacity: int = 1
    speed_kmh: float = 40.0


@router.get("/")
async def list_resources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resource))
    return result.scalars().all()


@router.post("/", status_code=201)
async def create_resource(payload: ResourceCreate, db: AsyncSession = Depends(get_db)):
    r = Resource(**payload.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.get("/deployments")
async def list_deployments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).order_by(Deployment.priority_rank))
    return result.scalars().all()


@router.patch("/deployments/{deployment_id}/approve")
async def approve_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    d = await db.get(Deployment, deployment_id)
    if not d:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Deployment not found")
    d.status = DeploymentStatus.APPROVED
    await db.commit()
    return {"status": "approved", "deployment_id": deployment_id}
