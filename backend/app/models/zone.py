"""
Zone = a geographic unit in the disaster graph.
Each zone is a node. Adjacency is stored in the ZoneEdge table.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    district = Column(String, nullable=False)

    # Geographic center (lat/lon — simple, no PostGIS required for MVP)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    # Demographics & vulnerability
    population = Column(Integer, default=0)
    vulnerability_index = Column(Float, default=0.5)   # 0..1, higher = more vulnerable
    elevation_m = Column(Float, default=0.0)           # metres above river level
    has_hospital = Column(Boolean, default=False)
    has_shelter = Column(Boolean, default=False)

    # Real-time state (updated by cascade engine)
    severity_score = Column(Float, default=0.0)        # 0..1
    flood_depth_m = Column(Float, default=0.0)
    time_to_critical_h = Column(Float, nullable=True)  # hours until critical threshold
    is_isolated = Column(Boolean, default=False)       # cut off from resources

    # Incident confidence (from MSEFE)
    incident_confidence = Column(Float, default=0.0)   # 0..1 Bayesian posterior

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    edges_from = relationship("ZoneEdge", foreign_keys="ZoneEdge.from_zone_id", back_populates="from_zone")
    edges_to = relationship("ZoneEdge", foreign_keys="ZoneEdge.to_zone_id", back_populates="to_zone")
    incidents = relationship("Incident", back_populates="zone")
    resources = relationship("Resource", back_populates="zone")


class ZoneEdge(Base):
    """
    Directed edge between two zones.
    Represents a road, river segment, or drainage path.
    """
    __tablename__ = "zone_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    to_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    # Edge type: 'road' | 'river' | 'drainage'
    edge_type = Column(String, default="road")

    # Road traversability (degrades as disaster progresses)
    passable = Column(Boolean, default=True)
    degradation_factor = Column(Float, default=1.0)   # 0..1 (1 = fully passable)
    travel_time_min = Column(Float, default=15.0)     # minutes at full capacity

    # River/drainage: flow capacity multiplier (used in flood propagation)
    flow_capacity = Column(Float, default=1.0)

    from_zone = relationship("Zone", foreign_keys=[from_zone_id], back_populates="edges_from")
    to_zone = relationship("Zone", foreign_keys=[to_zone_id], back_populates="edges_to")
