"""
Punjab/Sutlej River Basin — Flood Demo Seed Data
=================================================
Seeded scenario: July 2023 Sutlej flooding event (historically accurate locations).
12 zones across Ludhiana, Fazilka, Ferozepur, Moga districts.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.zone import Zone, ZoneEdge
from app.models.incident import Incident, IncidentSource, IncidentType
from app.models.resource import Resource, ResourceType, ResourceStatus


ZONES = [
    # id(logical), name, district, lat, lon, pop, vuln, elev_m, hosp, shelter
    (1,  "Harike Barrage",    "Ferozepur",  30.9562,  74.9385, 12000, 0.85, 220, False, True),
    (2,  "Ferozepur City",    "Ferozepur",  30.9253,  74.6218, 98000, 0.65, 225, True,  True),
    (3,  "Fazilka Town",      "Fazilka",    30.4000,  74.0300, 62000, 0.70, 215, True,  False),
    (4,  "Ludhiana Central",  "Ludhiana",   30.9010,  75.8573,490000, 0.40, 244, True,  True),
    (5,  "Moga",              "Moga",       30.8148,  75.1700,130000, 0.55, 232, True,  False),
    (6,  "Jagraon",           "Ludhiana",   30.7879,  75.4741, 75000, 0.60, 236, False, True),
    (7,  "Zira",              "Ferozepur",  30.9700,  74.9900, 28000, 0.75, 222, False, False),
    (8,  "Muktsar",           "Muktsar",    30.4771,  74.5157, 83000, 0.68, 218, True,  False),
    (9,  "Abohar",            "Fazilka",    30.1427,  74.1987, 77000, 0.72, 212, False, True),
    (10, "Dharamkot Village", "Moga",       30.8800,  75.0800,  3200, 0.92, 230, False, False),
    (11, "Rode Crossing",     "Moga",       30.7500,  75.3500,  8000, 0.88, 233, False, False),
    (12, "Goniana Mandi",     "Bathinda",   30.5200,  75.0200, 18000, 0.78, 220, False, True),
]

# (from_id, to_id, edge_type, pass, deg_factor, travel_min, flow_cap)
EDGES = [
    # Sutlej river corridor (source of flood propagation)
    (1, 7,  "river",    True,  1.0, 40,  1.5),
    (7, 2,  "river",    True,  1.0, 30,  1.5),
    (2, 3,  "river",    True,  1.0, 90,  1.2),
    (3, 9,  "river",    True,  1.0, 80,  1.0),
    (9, 8,  "drainage", True,  1.0, 60,  0.8),
    # Road network
    (4, 6,  "road",     True,  1.0, 45,  1.0),
    (6, 5,  "road",     True,  1.0, 35,  1.0),
    (5, 7,  "road",     True,  1.0, 50,  1.0),
    (5, 11, "road",     True,  1.0, 25,  1.0),
    (11, 6, "road",     True,  1.0, 30,  1.0),
    (5, 10, "road",     True,  1.0, 20,  1.0),
    (6, 12, "road",     True,  1.0, 55,  1.0),
    (12, 8, "road",     True,  1.0, 65,  1.0),
    (8, 3,  "road",     True,  1.0, 70,  1.0),
    (2, 7,  "road",     True,  1.0, 30,  1.0),
    (4, 5,  "road",     True,  1.0, 60,  1.0),
    # Bi-directional road corrections (reverse direction)
    (6, 4,  "road",     True,  1.0, 45,  1.0),
    (5, 6,  "road",     True,  1.0, 35,  1.0),
    (7, 5,  "road",     True,  1.0, 50,  1.0),
    (11, 5, "road",     True,  1.0, 25,  1.0),
]

# Initial flood scenario state: Harike Barrage at peak discharge
INITIAL_SEVERITY = {
    1: 0.92,   # Harike Barrage — CRITICAL (peak discharge)
    7: 0.78,   # Zira — HIGH
    2: 0.65,   # Ferozepur City — HIGH
    10: 0.55,  # Dharamkot Village — MODERATE (isolated)
    11: 0.50,  # Rode Crossing — MODERATE
    5: 0.35,   # Moga — LOW-MODERATE
    3: 0.30,   # Fazilka — LOW
    6: 0.20,   # Jagraon — LOW
}

INITIAL_INCIDENTS = [
    # zone_id, source, type, severity, description
    (1,  "authority",  "flood",           0.95, "BBMB reports Harike dam at 98% capacity, 18,000 cusecs discharge"),
    (7,  "imd",        "flood",           0.82, "IMD red alert: rainfall 120mm/24h at Zira"),
    (2,  "citizen",    "trapped_people",  0.70, "Multiple families stranded in Bhagwanpura colony"),
    (2,  "authority",  "road_blocked",    0.80, "NH-95 Ferozepur bypass under 4ft water"),
    (10, "social",     "trapped_people",  0.60, "Twitter reports: 200+ villagers cut off in Dharamkot"),
    (10, "citizen",    "flood",           0.75, "Voice call: water entered homes, no boat available"),
    (11, "citizen",    "bridge_failure",  0.85, "Rode bridge cracked, villagers can't cross to Moga"),
    (5,  "imd",        "flood",           0.45, "IMD yellow alert: Sutlej levels rising at Moga gauge"),
    (1,  "satellite",  "flood",           0.90, "Sentinel-2 SAR: 14 sq km inundated around Harike wetland"),
]

RESOURCES = [
    # name, type, qty, zone_id, capacity, speed
    ("NDRF Team Alpha",   "ndrf_team",    1, 4,    45, 40),
    ("NDRF Team Beta",    "ndrf_team",    1, 4,    45, 40),
    ("Rescue Boat #1",    "rescue_boat",  1, 2,    12, 25),
    ("Rescue Boat #2",    "rescue_boat",  1, 4,    12, 25),
    ("Rescue Boat #3",    "rescue_boat",  1, 4,    12, 25),
    ("Helicopter Alpha",  "helicopter",   1, 4,    20, 120),
    ("Ambulance Batch-1", "ambulance",    3, 4,     4, 60),
    ("Food Packets-1",    "food_packet", 50, 4,   100, 40),
    ("Food Packets-2",    "food_packet", 30, 5,   100, 40),
    ("Medical Kit-1",     "medical_kit", 10, 4,     1, 40),
    ("Shelter Slots-Fzp", "shelter_slot",200, 2,    1, 0),
    ("Shelter Slots-Lud", "shelter_slot",500, 4,    1, 0),
]


async def seed(db: AsyncSession):
    """Insert demo data if zones table is empty."""
    from sqlalchemy import select, func
    count = (await db.execute(select(func.count()).select_from(Zone))).scalar()
    if count and count > 0:
        print(f"⏭️  Seed skipped — {count} zones already in DB")
        return

    print("🌱  Seeding Punjab/Sutlej flood scenario...")

    # Zones
    zone_objs = {}
    for zd in ZONES:
        zid, name, district, lat, lon, pop, vuln, elev, hosp, shelter = zd
        z = Zone(
            id=zid, name=name, district=district,
            lat=lat, lon=lon, population=pop,
            vulnerability_index=vuln, elevation_m=elev,
            has_hospital=hosp, has_shelter=shelter,
            severity_score=INITIAL_SEVERITY.get(zid, 0.0),
        )
        db.add(z)
        zone_objs[zid] = z

    await db.flush()

    # Edges
    for ed in EDGES:
        fid, tid, etype, passable, deg, travel, flow = ed
        db.add(ZoneEdge(
            from_zone_id=fid, to_zone_id=tid,
            edge_type=etype, passable=passable,
            degradation_factor=deg, travel_time_min=travel,
            flow_capacity=flow,
        ))

    # Incidents
    from app.models.incident import SOURCE_TRUST
    src_map = {
        "authority": IncidentSource.AUTHORITY,
        "imd": IncidentSource.IMD_WEATHER,
        "citizen": IncidentSource.CITIZEN,
        "satellite": IncidentSource.SATELLITE,
        "social": IncidentSource.SOCIAL_MEDIA,
    }
    type_map = {
        "flood": IncidentType.FLOOD,
        "road_blocked": IncidentType.ROAD_BLOCKED,
        "bridge_failure": IncidentType.BRIDGE_FAILURE,
        "trapped_people": IncidentType.TRAPPED_PEOPLE,
    }
    for inc in INITIAL_INCIDENTS:
        zid, src_str, itype_str, sev, desc = inc
        src = src_map[src_str]
        db.add(Incident(
            zone_id=zid, source=src,
            incident_type=type_map[itype_str],
            severity=sev, description=desc,
            trust_weight=SOURCE_TRUST[src],
            is_verified=(src in (IncidentSource.AUTHORITY, IncidentSource.IMD_WEATHER)),
            corroboration_count=2 if zid in (1, 10) else 1,
        ))

    # Resources
    rtype_map = {
        "ndrf_team": ResourceType.NDRF_TEAM,
        "rescue_boat": ResourceType.RESCUE_BOAT,
        "helicopter": ResourceType.HELICOPTER,
        "ambulance": ResourceType.AMBULANCE,
        "food_packet": ResourceType.FOOD_PACKET,
        "medical_kit": ResourceType.MEDICAL_KIT,
        "shelter_slot": ResourceType.SHELTER_SLOT,
    }
    for res in RESOURCES:
        name, rtype, qty, zone_id, cap, speed = res
        db.add(Resource(
            name=name, resource_type=rtype_map[rtype],
            quantity=qty, zone_id=zone_id,
            capacity=cap, speed_kmh=speed,
            status=ResourceStatus.AVAILABLE,
        ))

    await db.commit()
    print("✅  Seed complete — 12 zones, edges, incidents, resources loaded")
