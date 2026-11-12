"""
Resource = a deployable unit (ambulance, rescue boat, supplies, shelter capacity).
Deployment = a routing directive issued by the optimizer.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class ResourceType(str, enum.Enum):
    RESCUE_BOAT = "rescue_boat"
    AMBULANCE = "ambulance"
    HELICOPTER = "helicopter"
    FOOD_PACKET = "food_packet"       # in units of 100
    MEDICAL_KIT = "medical_kit"
    SHELTER_SLOT = "shelter_slot"     # capacity units
    NDRF_TEAM = "ndrf_team"           # 45-person team


class ResourceStatus(str, enum.Enum):
    AVAILABLE = "available"
    DEPLOYED = "deployed"
    IN_TRANSIT = "in_transit"
    DEPLETED = "depleted"


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    status = Column(Enum(ResourceStatus), default=ResourceStatus.AVAILABLE)

    quantity = Column(Integer, default=1)           # units available
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)  # current location

    # Capability metadata
    capacity = Column(Integer, default=1)           # people/units per trip
    speed_kmh = Column(Float, default=40.0)         # for travel time calculation

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    zone = relationship("Zone", back_populates="resources")
    deployments = relationship("Deployment", back_populates="resource")


class DeploymentStatus(str, enum.Enum):
    RECOMMENDED = "recommended"   # optimizer output, awaiting human approval
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Deployment(Base):
    """
    A resource deployment directive from the optimizer.
    Human operator approves/rejects before it becomes active.
    """
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    from_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    to_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    status = Column(Enum(DeploymentStatus), default=DeploymentStatus.RECOMMENDED)
    priority_rank = Column(Integer, default=0)    # lower = more urgent

    # Optimizer reasoning (shown in UI as explainability)
    rationale = Column(String, nullable=True)
    urgency_score = Column(Float, default=0.0)
    estimated_travel_min = Column(Float, nullable=True)
    deadline_minutes = Column(Float, nullable=True)  # act-by window

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resource = relationship("Resource", back_populates="deployments")
