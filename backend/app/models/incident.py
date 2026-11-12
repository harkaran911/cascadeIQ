"""
Incident = a reported event from any source.
MSEFE fuses these to produce incident_confidence on each Zone.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class IncidentSource(str, enum.Enum):
    CITIZEN = "citizen"       # form submission
    IMD_WEATHER = "imd"       # India Met Dept / OpenWeather
    SATELLITE = "satellite"   # satellite feed
    SOCIAL_MEDIA = "social"   # NLP-extracted
    AUTHORITY = "authority"   # official report (highest trust)


class IncidentType(str, enum.Enum):
    FLOOD = "flood"
    ROAD_BLOCKED = "road_blocked"
    BRIDGE_FAILURE = "bridge_failure"
    POWER_OUTAGE = "power_outage"
    TRAPPED_PEOPLE = "trapped_people"
    MEDICAL_EMERGENCY = "medical_emergency"
    INFRASTRUCTURE_DAMAGE = "infrastructure_damage"


# Source trust weights — used by MSEFE
SOURCE_TRUST = {
    IncidentSource.AUTHORITY: 0.95,
    IncidentSource.IMD_WEATHER: 0.85,
    IncidentSource.SATELLITE: 0.80,
    IncidentSource.CITIZEN: 0.40,
    IncidentSource.SOCIAL_MEDIA: 0.25,
}


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    source = Column(Enum(IncidentSource), nullable=False)
    incident_type = Column(Enum(IncidentType), nullable=False)

    severity = Column(Float, default=0.5)   # 0..1 as reported by source
    description = Column(String, nullable=True)

    # Metadata
    reporter_name = Column(String, nullable=True)
    reporter_contact = Column(String, nullable=True)

    # MSEFE processing
    trust_weight = Column(Float, default=0.4)
    is_verified = Column(Boolean, default=False)
    corroboration_count = Column(Integer, default=1)  # how many sources agree

    # AI classification — Phase 6 (Groq llama-3.1-8b-instant)
    ai_incident_type = Column(String, nullable=True)   # validated incident_type or None
    ai_severity      = Column(Float,  nullable=True)   # 0..1 severity estimate
    ai_confidence    = Column(Float,  nullable=True)   # 0..1 classifier confidence
    ai_keywords      = Column(String, nullable=True)   # JSON array ["word1", "word2"]
    ai_reasoning     = Column(String, nullable=True)   # one-sentence explanation

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    zone = relationship("Zone", back_populates="incidents")
