"""
Cascading Temporal Disaster Graph (CTDG) Engine
================================================
Implements spatiotemporal hazard propagation through the zone graph.
- Nodes = Zone rows in DB
- Edges = ZoneEdge rows (road / river / drainage)
- Each propagation tick advances the disaster state forward in time.

Key physics rules:
  flood propagation: flows from higher-severity upstream zones along
  river/drainage edges, attenuated by degradation_factor and flow_capacity.

  road degradation: severity above threshold degrades edges, raising
  travel_time and eventually marking them impassable.

  isolation detection: zone is_isolated if no passable path to any
  resource hub (BFS on passable edges).
"""
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.zone import Zone, ZoneEdge


# Propagation thresholds
FLOOD_PROPAGATION_THRESHOLD = 0.3   # severity above which a zone starts affecting neighbours
ROAD_IMPASSABLE_THRESHOLD = 0.75    # degradation_factor below which edge is impassable


async def build_graph(db: AsyncSession) -> tuple[nx.DiGraph, dict, dict]:
    """Load zones + edges from DB and build a NetworkX DiGraph."""
    zones_result = await db.execute(select(Zone))
    zones = {z.id: z for z in zones_result.scalars().all()}

    edges_result = await db.execute(select(ZoneEdge))
    edges = edges_result.scalars().all()

    G = nx.DiGraph()
    for z in zones.values():
        G.add_node(z.id, severity=z.severity_score, isolated=z.is_isolated,
                   vulnerability=z.vulnerability_index, flood_depth=z.flood_depth_m)

    for e in edges:
        G.add_edge(
            e.from_zone_id, e.to_zone_id,
            edge_type=e.edge_type,
            passable=e.passable,
            degradation_factor=e.degradation_factor,
            travel_time_min=e.travel_time_min,
            flow_capacity=e.flow_capacity,
            edge_id=e.id,
        )

    return G, zones, {e.id: e for e in edges}


async def propagate_cascade(db: AsyncSession, ticks: int = 1):
    """
    Run `ticks` propagation steps.
    Each tick:
      1. Propagate flood severity along river/drainage edges.
      2. Degrade road edges based on adjacent zone severity.
      3. Detect isolated zones (no passable path to resource hub).
      4. Write updated state back to DB.
    """
    G, zones, edge_map = await build_graph(db)
    updated_zones = {}
    updated_edges = {}

    for _ in range(ticks):
        new_severity = {nid: G.nodes[nid]["severity"] for nid in G.nodes}

        # ── Step 1: flood propagation ────────────────────────────────────────
        for u, v, data in G.edges(data=True):
            if data["edge_type"] in ("river", "drainage"):
                upstream_sev = G.nodes[u]["severity"]
                if upstream_sev >= FLOOD_PROPAGATION_THRESHOLD:
                    propagated = (
                        upstream_sev
                        * data["flow_capacity"]
                        * data["degradation_factor"]
                        * 0.6   # attenuation factor
                    )
                    new_severity[v] = min(1.0, max(new_severity[v], propagated))

        # ── Step 2: road degradation ─────────────────────────────────────────
        for u, v, data in G.edges(data=True):
            if data["edge_type"] == "road":
                avg_sev = (G.nodes[u]["severity"] + G.nodes[v]["severity"]) / 2
                # Degrade proportional to average severity
                new_deg = max(0.0, data["degradation_factor"] - avg_sev * 0.15)
                data["degradation_factor"] = new_deg
                data["passable"] = new_deg >= ROAD_IMPASSABLE_THRESHOLD
                # Adjusted travel time — impassable roads take 999 min
                data["travel_time_min"] = (
                    data["travel_time_min"] / max(new_deg, 0.01)
                    if data["passable"] else 999.0
                )
                if "edge_id" in data:
                    updated_edges[data["edge_id"]] = {
                        "degradation_factor": new_deg,
                        "passable": data["passable"],
                        "travel_time_min": data["travel_time_min"],
                    }

        for nid in G.nodes:
            G.nodes[nid]["severity"] = new_severity[nid]
            updated_zones[nid] = new_severity[nid]

        # ── Step 3: isolation detection ──────────────────────────────────────
        # A zone is isolated if no passable path exists to ANY hospital/shelter zone
        resource_hubs = {nid for nid, z in zones.items() if z.has_hospital or z.has_shelter}
        passable_G = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            if data.get("passable", True):
                passable_G.add_edge(u, v)

        for nid in G.nodes:
            reachable = nx.descendants(passable_G, nid) | {nid}
            is_isolated = len(reachable & resource_hubs) == 0
            G.nodes[nid]["isolated"] = is_isolated

    # ── Write back to DB ─────────────────────────────────────────────────────
    for zone_id, new_sev in updated_zones.items():
        zone = zones[zone_id]
        zone.severity_score = new_sev
        zone.is_isolated = G.nodes[zone_id]["isolated"]
        # Estimate time_to_critical: if severity < 0.8, linear extrapolation
        if new_sev < 0.8:
            remaining = (0.8 - new_sev) / max(0.01, new_sev)
            zone.time_to_critical_h = round(remaining * 6, 1)  # rough hours
        else:
            zone.time_to_critical_h = 0.0
        db.add(zone)

    for edge_id, changes in updated_edges.items():
        edge = edge_map[edge_id]
        for k, v in changes.items():
            setattr(edge, k, v)
        db.add(edge)

    await db.commit()
    return {"ticks": ticks, "zones_updated": len(updated_zones), "edges_updated": len(updated_edges)}


async def get_cascade_snapshot(db: AsyncSession) -> dict:
    """Return the current graph state for the frontend."""
    G, zones, _ = await build_graph(db)
    return {
        "nodes": [
            {
                "id": z.id, "name": z.name, "lat": z.lat, "lon": z.lon,
                "severity_score": z.severity_score,
                "incident_confidence": z.incident_confidence,
                "is_isolated": z.is_isolated,
                "time_to_critical_h": z.time_to_critical_h,
                "vulnerability_index": z.vulnerability_index,
            }
            for z in zones.values()
        ],
        "edges": [
            {
                "from": u, "to": v,
                "passable": data.get("passable", True),
                "degradation_factor": data.get("degradation_factor", 1.0),
                "edge_type": data.get("edge_type", "road"),
            }
            for u, v, data in G.edges(data=True)
        ],
    }
