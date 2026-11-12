"""
Predictive Resource Optimizer (PRO)
====================================
Two-stage optimizer for disaster resource allocation.

Stage A — Pre-positioning (stochastic facility location):
  Given rainfall forecast severity, decide WHICH staging zones should
  hold pre-positioned stocks before the flood peaks.
  Implemented as a weighted coverage LP using PuLP.

Stage B — Real-time routing (priority-ranked greedy + LP):
  Given current zone risk scores, assign available resources to
  critical zones, respecting road passability and travel time.
  Returns deployment directives written to the Deployment table.

The optimizer explicitly weights vulnerability_index so that the
poorest/least-served communities don't get skipped in favour of
more accessible ones.
"""
from pulp import LpProblem, LpVariable, LpMaximize, lpSum, LpBinary, value, PULP_CBC_CMD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.zone import Zone, ZoneEdge
from app.models.resource import Resource, ResourceStatus, Deployment, DeploymentStatus
import networkx as nx


# ── Weight knobs ────────────────────────────────────────────────────────────
W_SEVERITY      = 0.40
W_CONFIDENCE    = 0.25
W_VULNERABILITY = 0.25
W_POPULATION    = 0.10

TRAVEL_TIME_PENALTY = 0.005   # per minute — discounts far resources slightly
MAX_TRAVEL_MIN = 120           # ignore edges beyond 2 h travel time


def _zone_priority(zone: Zone) -> float:
    """Composite priority score for a zone. Higher = needs help more urgently."""
    pop_factor = min(1.0, zone.population / 100_000)   # normalise to 0..1
    return (
        W_SEVERITY      * zone.severity_score
        + W_CONFIDENCE  * zone.incident_confidence
        + W_VULNERABILITY * zone.vulnerability_index
        + W_POPULATION  * pop_factor
    )


async def _build_passable_graph(db: AsyncSession):
    """Build a travel-time graph restricted to passable edges."""
    edges_result = await db.execute(select(ZoneEdge).where(ZoneEdge.passable == True))  # noqa: E712
    edges = edges_result.scalars().all()
    G = nx.DiGraph()
    for e in edges:
        if e.travel_time_min <= MAX_TRAVEL_MIN:
            G.add_edge(e.from_zone_id, e.to_zone_id,
                       weight=e.travel_time_min,
                       degradation=e.degradation_factor)
    return G


async def run_optimization(db: AsyncSession) -> list[dict]:
    """
    Run Stage B real-time allocation.
    Returns list of deployment directive dicts (also written to DB).
    """
    # Load current state
    zones_result = await db.execute(select(Zone))
    zones = {z.id: z for z in zones_result.scalars().all()}

    resources_result = await db.execute(
        select(Resource).where(Resource.status == ResourceStatus.AVAILABLE)
    )
    available = resources_result.scalars().all()

    if not zones or not available:
        return []

    passable_G = await _build_passable_graph(db)

    # Rank zones by priority — only consider those above a threshold
    ranked_zones = sorted(
        [z for z in zones.values() if _zone_priority(z) > 0.2],
        key=_zone_priority,
        reverse=True,
    )

    if not ranked_zones:
        return []

    # ── PuLP LP: maximise weighted coverage ────────────────────────────────
    prob = LpProblem("cascade_resource_allocation", LpMaximize)

    # Decision variables: x[r_id][z_id] = 1 if resource r is sent to zone z
    x = {}
    feasible_pairs = []
    travel_times = {}

    for r in available:
        for z in ranked_zones:
            # Check if there's a passable path from resource's current zone to target
            r_zone = r.zone_id
            if r_zone is None or r_zone not in passable_G or z.id not in passable_G:
                continue
            try:
                tt = nx.shortest_path_length(passable_G, r_zone, z.id, weight="weight")
            except nx.NetworkXNoPath:
                continue
            if tt > MAX_TRAVEL_MIN:
                continue

            var = LpVariable(f"x_{r.id}_{z.id}", cat=LpBinary)
            x[(r.id, z.id)] = var
            feasible_pairs.append((r, z, tt))
            travel_times[(r.id, z.id)] = tt

    if not feasible_pairs:
        # Fallback: nearest available resource to highest-priority zone
        return _greedy_fallback(available, ranked_zones, zones, db)

    # Objective: maximise priority coverage minus travel penalty
    prob += lpSum(
        _zone_priority(z) * x[(r.id, z.id)]
        - TRAVEL_TIME_PENALTY * travel_times[(r.id, z.id)] * x[(r.id, z.id)]
        for r, z, tt in feasible_pairs
        if (r.id, z.id) in x
    )

    # Constraint 1: each resource deployed to at most 1 zone
    for r in available:
        assigned = [x[(r.id, z.id)] for _, z, _ in feasible_pairs
                    if (r.id, z.id) in x and _ == r]
        # Reconstruct correctly
        assigned = [x[(r.id, z.id)] for z in ranked_zones if (r.id, z.id) in x]
        if assigned:
            prob += lpSum(assigned) <= 1

    # Constraint 2: each critical zone gets at most 3 resources (avoid over-saturation)
    for z in ranked_zones:
        assigned = [x[(r.id, z.id)] for r in available if (r.id, z.id) in x]
        if assigned:
            prob += lpSum(assigned) <= 3

    prob.solve(PULP_CBC_CMD(msg=0))

    # Extract solution
    directives = []
    rank = 0
    for r, z, tt in feasible_pairs:
        key = (r.id, z.id)
        if key in x and value(x[key]) and value(x[key]) > 0.5:
            priority = _zone_priority(z)
            rationale = (
                f"Zone '{z.name}' priority={priority:.2f} "
                f"(sev={z.severity_score:.2f}, conf={z.incident_confidence:.2f}, "
                f"vuln={z.vulnerability_index:.2f}). "
                f"Travel time {tt:.0f} min via passable roads."
            )
            dep = Deployment(
                resource_id=r.id,
                from_zone_id=r.zone_id,
                to_zone_id=z.id,
                status=DeploymentStatus.RECOMMENDED,
                priority_rank=rank,
                urgency_score=round(priority, 4),
                estimated_travel_min=round(tt, 1),
                deadline_minutes=round(z.time_to_critical_h * 60, 1) if z.time_to_critical_h else None,
                rationale=rationale,
            )
            db.add(dep)
            directives.append({
                "resource_id": r.id,
                "resource_name": r.name,
                "from_zone_id": r.zone_id,
                "to_zone_id": z.id,
                "zone_name": z.name,
                "priority_rank": rank,
                "urgency_score": round(priority, 4),
                "estimated_travel_min": round(tt, 1),
                "rationale": rationale,
            })
            rank += 1

    await db.commit()
    return directives


def _greedy_fallback(available, ranked_zones, zones, db) -> list[dict]:
    """
    Dead-simple greedy fallback when no passable paths exist (full isolation).
    Just return the top-priority zone paired with the first available resource.
    """
    if not available or not ranked_zones:
        return []
    top_zone = ranked_zones[0]
    r = available[0]
    return [{
        "resource_id": r.id,
        "resource_name": r.name,
        "from_zone_id": r.zone_id,
        "to_zone_id": top_zone.id,
        "zone_name": top_zone.name,
        "priority_rank": 0,
        "urgency_score": round(_zone_priority(top_zone), 4),
        "estimated_travel_min": None,
        "rationale": "FALLBACK — all roads impassable. Helicopter/boat deployment required.",
    }]
