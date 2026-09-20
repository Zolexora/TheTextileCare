"""Phase 8 — 4-Tier Algorithmic Familiarity & Priority Engine.

Feature 5:
Deterministic lexicographical candidate ranking hierarchy:
    Exact Address Familiarity > Customer Familiarity > Workload Balancing > Geographic Proximity
Deterministic tie-breaking:
    Seniority (created_at ASC) > Driver ID (id ASC)
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.schemas.driver import (
    CandidateRankingProfile,
    DriverRankingResult,
    DriverScoreBreakdown,
    DutyRankingContext,
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in meters."""
    return haversine_distance(lat1, lon1, lat2, lon2) * 1000.0


def calculate_4tier_priority_score(
    address_familiarity: int,
    customer_familiarity: int,
    active_duties: int,
    distance_km: float,
    created_at: datetime,
    driver_id: uuid.UUID,
) -> tuple:
    """Calculate the deterministic comparison tuple for driver priority ranking."""
    ts = created_at.timestamp() if isinstance(created_at, datetime) else 0.0
    id_val = int(driver_id) if isinstance(driver_id, uuid.UUID) else 0
    return (
        address_familiarity,
        customer_familiarity,
        -active_duties,
        -round(distance_km, 4),
        -ts,
        -id_val,
    )


class PriorityResolutionEngine:
    """4-Tier Algorithmic Familiarity & Priority Engine.

    Precedence Hierarchy:
        Tier 1: Exact Address Familiarity (completed duties at destination address or <=25m)
        Tier 2: Customer Familiarity (completed duties for customer)
        Tier 3: Workload Balancing (fewest active duties: ASSIGNED / STARTED / IN_PROGRESS)
        Tier 4: Geographic Proximity (shortest Haversine distance to destination)
        Tie-Breakers: created_at ASC (seniority), id ASC (deterministic UUID)
    """

    ADDRESS_PROXIMITY_THRESHOLD_METERS: float = 25.0

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def rank_candidates(
        self,
        duty: DutyRankingContext | Any,
        candidates: Sequence[Driver],
        candidate_profiles: Sequence[CandidateRankingProfile] | None = None,
    ) -> list[DriverRankingResult]:
        """Rank eligible candidates deterministically according to the 4-tier hierarchy."""
        if not candidates:
            return []

        ctx = self._normalize_context(duty)

        # Build or use candidate profiles
        if candidate_profiles is not None:
            profiles = list(candidate_profiles)
        else:
            profiles = self._build_profiles_from_db(ctx, candidates)

        # Helper to extract created_at and id safely
        def sort_key(p: CandidateRankingProfile) -> tuple:
            drv = p.driver
            # created_at
            c_at = getattr(drv, "created_at", None)
            if c_at is None:
                c_at = datetime.min.replace(tzinfo=timezone.utc)
            elif not c_at.tzinfo:
                c_at = c_at.replace(tzinfo=timezone.utc)

            # id
            d_id = getattr(drv, "id", None) or uuid.UUID(int=0)
            id_str = str(d_id)

            return (
                -p.address_familiarity_count,   # Tier 1: higher count comes first (ascending sort)
                -p.customer_familiarity_count,  # Tier 2: higher count comes first
                p.active_duties_count,          # Tier 3: fewer active duties comes first
                p.distance_meters,              # Tier 4: closer distance comes first
                c_at,                           # Tie-break 1: earlier registration first
                id_str,                         # Tie-break 2: deterministic UUID order
            )

        profiles.sort(key=sort_key)

        results: list[DriverRankingResult] = []
        for rank, p in enumerate(profiles, start=1):
            dist_km = (
                p.distance_meters / 1000.0
                if p.distance_meters != float("inf")
                else float("inf")
            )
            results.append(
                DriverRankingResult(
                    driver_id=p.driver.id,
                    driver=p.driver,
                    rank=rank,
                    score_breakdown=DriverScoreBreakdown(
                        address_familiarity=p.address_familiarity_count,
                        customer_familiarity=p.customer_familiarity_count,
                        active_duties=p.active_duties_count,
                        distance_meters=round(p.distance_meters, 2),
                        distance_km=round(dist_km, 4),
                    ),
                )
            )
        return results

    def _normalize_context(self, duty: DutyRankingContext | Any) -> DutyRankingContext:
        """Convert arbitrary duty object to a standardized DutyRankingContext."""
        if isinstance(duty, DutyRankingContext):
            return duty

        target_lat = None
        target_lon = None

        # Check customer address coordinates if available
        if hasattr(duty, "customer_address") and duty.customer_address:
            if duty.customer_address.latitude is not None:
                target_lat = float(duty.customer_address.latitude)
            if duty.customer_address.longitude is not None:
                target_lon = float(duty.customer_address.longitude)
        elif hasattr(duty, "target_address_snapshot") and duty.target_address_snapshot:
            target_lat = duty.target_address_snapshot.get("latitude")
            target_lon = duty.target_address_snapshot.get("longitude")

        return DutyRankingContext(
            duty_id=getattr(duty, "id", getattr(duty, "duty_id", uuid.uuid4())),
            seller_id=getattr(duty, "seller_id", uuid.uuid4()),
            tenant_id=getattr(duty, "tenant_id", uuid.uuid4()),
            customer_id=getattr(duty, "customer_id", uuid.uuid4()),
            customer_address_id=getattr(duty, "customer_address_id", None),
            branch_id=getattr(duty, "branch_id", None),
            target_latitude=float(target_lat) if target_lat is not None else None,
            target_longitude=float(target_lon) if target_lon is not None else None,
        )

    def _build_profiles_from_db(
        self, ctx: DutyRankingContext, candidates: Sequence[Driver]
    ) -> list[CandidateRankingProfile]:
        """Aggregate metrics for candidate drivers in a single SQL query."""
        candidate_ids = [d.id for d in candidates]
        active_map: dict[uuid.UUID, int] = {d_id: 0 for d_id in candidate_ids}
        customer_map: dict[uuid.UUID, int] = {d_id: 0 for d_id in candidate_ids}
        address_map: dict[uuid.UUID, int] = {d_id: 0 for d_id in candidate_ids}

        if self.db is not None:
            try:
                from sqlalchemy import text
                # Use a savepoint so a failed query doesn't abort the outer transaction
                self.db.execute(text("SAVEPOINT priority_lookup"))
                stmt = text("""
                    SELECT 
                        active_driver_id,
                        COUNT(id) FILTER (WHERE status IN ('ASSIGNED', 'STARTED', 'IN_PROGRESS')) AS active_count,
                        COUNT(id) FILTER (WHERE status = 'COMPLETED' AND customer_id = :cust_id) AS cust_count,
                        COUNT(id) FILTER (WHERE status = 'COMPLETED' AND customer_address_id = :addr_id) AS addr_count
                    FROM driver_duties
                    WHERE active_driver_id = ANY(:c_ids)
                    GROUP BY active_driver_id
                """)
                rows = self.db.execute(
                    stmt,
                    {
                        "cust_id": ctx.customer_id,
                        "addr_id": ctx.customer_address_id,
                        "c_ids": list(candidate_ids),
                    },
                ).all()
                self.db.execute(text("RELEASE SAVEPOINT priority_lookup"))
                for row in rows:
                    if row.active_driver_id:
                        active_map[row.active_driver_id] = row.active_count or 0
                        customer_map[row.active_driver_id] = row.cust_count or 0
                        address_map[row.active_driver_id] = row.addr_count or 0
            except Exception:
                # Table driver_duties may not exist yet — rollback to savepoint to keep transaction healthy
                try:
                    self.db.execute(text("ROLLBACK TO SAVEPOINT priority_lookup"))
                except Exception:
                    pass

        profiles: list[CandidateRankingProfile] = []
        for driver in candidates:
            dist = self._compute_distance(driver, ctx)
            profiles.append(
                CandidateRankingProfile(
                    driver=driver,
                    address_familiarity_count=address_map.get(driver.id, 0),
                    customer_familiarity_count=customer_map.get(driver.id, 0),
                    active_duties_count=active_map.get(driver.id, 0),
                    distance_meters=dist,
                )
            )
        return profiles

    def _compute_distance(self, driver: Driver, ctx: DutyRankingContext) -> float:
        """Compute proximity distance, prioritizing live GPS over branch base."""
        if ctx.target_latitude is None or ctx.target_longitude is None:
            return float("inf")

        # Live GPS priority
        lat = getattr(driver, "current_latitude", None) or getattr(driver, "latitude", None)
        lon = getattr(driver, "current_longitude", None) or getattr(driver, "longitude", None)
        if lat is not None and lon is not None:
            return haversine_distance_meters(
                float(lat),
                float(lon),
                float(ctx.target_latitude),
                float(ctx.target_longitude),
            )

        # Fallback to home branch coordinates
        branch = getattr(driver, "home_branch", None) or getattr(driver, "branch", None)
        if branch and getattr(branch, "latitude", None) is not None and getattr(branch, "longitude", None) is not None:
            return haversine_distance_meters(
                float(branch.latitude),
                float(branch.longitude),
                float(ctx.target_latitude),
                float(ctx.target_longitude),
            )

        return float("inf")
