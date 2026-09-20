"""Unit tests for PriorityResolutionEngine (Milestone 1).

Validates deterministic 4-tier lexicographical ranking hierarchy:
Tier 1: Exact Address Familiarity (completed duties at destination)
Tier 2: Customer Familiarity (completed duties for customer)
Tier 3: Workload Balancing (fewest active duties)
Tier 4: Geographic Proximity (Haversine distance)
Tie-breakers: Seniority (created_at ASC) then id ASC.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.models.driver import Driver
from app.schemas.driver import (
    CandidateRankingProfile,
    DutyRankingContext,
)
from app.services.priority_engine import (
    PriorityResolutionEngine,
    haversine_distance,
    haversine_distance_meters,
)
from tests.conftest import create_test_driver, create_test_tenant


def _make_candidate(
    name: str = "Driver",
    created_at: datetime | None = None,
    driver_id: uuid.UUID | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> Driver:
    d = Driver(
        id=driver_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name=name,
        phone_number="+15550000000",
        current_latitude=lat,
        current_longitude=lon,
    )
    if created_at is not None:
        d.created_at = created_at
    else:
        d.created_at = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    return d


def test_tier1_address_familiarity_dominates():
    """Tier 1 wins over all other tiers: Higher exact address familiarity ranks #1,
    even if opponent has 10x customer familiarity, 0 workload, and is closer.
    """
    driver_a = _make_candidate(name="Driver A (Address Master)")
    driver_b = _make_candidate(name="Driver B (Customer Favorite)")

    profile_a = CandidateRankingProfile(
        driver=driver_a,
        address_familiarity_count=3,
        customer_familiarity_count=0,
        active_duties_count=2,
        distance_meters=15000.0,
    )
    profile_b = CandidateRankingProfile(
        driver=driver_b,
        address_familiarity_count=0,
        customer_familiarity_count=20,
        active_duties_count=0,
        distance_meters=300.0,
    )

    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )

    engine = PriorityResolutionEngine()
    results = engine.rank_candidates(
        duty=ctx,
        candidates=[driver_b, driver_a],
        candidate_profiles=[profile_b, profile_a],
    )

    assert len(results) == 2
    assert results[0].driver.id == driver_a.id
    assert results[0].rank == 1
    assert results[0].address_familiarity_score == 3
    assert results[1].driver.id == driver_b.id
    assert results[1].rank == 2


def test_tier2_customer_familiarity_dominates_when_address_tied():
    """Tier 2 wins over Tier 3: When address familiarity is tied, customer familiarity decides."""
    driver_a = _make_candidate(name="Driver A")
    driver_b = _make_candidate(name="Driver B")

    profile_a = CandidateRankingProfile(
        driver=driver_a,
        address_familiarity_count=1,
        customer_familiarity_count=5,
        active_duties_count=2,
        distance_meters=5000.0,
    )
    profile_b = CandidateRankingProfile(
        driver=driver_b,
        address_familiarity_count=1,
        customer_familiarity_count=1,
        active_duties_count=0,
        distance_meters=200.0,
    )

    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )

    engine = PriorityResolutionEngine()
    results = engine.rank_candidates(
        duty=ctx,
        candidates=[driver_b, driver_a],
        candidate_profiles=[profile_b, profile_a],
    )

    assert results[0].driver.id == driver_a.id
    assert results[0].customer_familiarity_score == 5
    assert results[1].driver.id == driver_b.id


def test_tier3_workload_balancing_dominates_when_familiarity_tied():
    """Tier 3 wins over Tier 4: Driver with fewer active duties ranks higher when familiarities are tied."""
    driver_a = _make_candidate(name="Driver A")
    driver_b = _make_candidate(name="Driver B")

    profile_a = CandidateRankingProfile(
        driver=driver_a,
        address_familiarity_count=2,
        customer_familiarity_count=3,
        active_duties_count=0,
        distance_meters=10000.0,
    )
    profile_b = CandidateRankingProfile(
        driver=driver_b,
        address_familiarity_count=2,
        customer_familiarity_count=3,
        active_duties_count=2,
        distance_meters=400.0,
    )

    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )

    engine = PriorityResolutionEngine()
    results = engine.rank_candidates(
        duty=ctx,
        candidates=[driver_b, driver_a],
        candidate_profiles=[profile_b, profile_a],
    )

    assert results[0].driver.id == driver_a.id
    assert results[0].active_workload == 0
    assert results[1].driver.id == driver_b.id
    assert results[1].active_workload == 2


def test_tier4_geographic_proximity_dominates_when_workload_tied():
    """Tier 4: Closer driver ranks higher when familiarity and workload are equal."""
    driver_a = _make_candidate(name="Driver A")
    driver_b = _make_candidate(name="Driver B")

    profile_a = CandidateRankingProfile(
        driver=driver_a,
        address_familiarity_count=0,
        customer_familiarity_count=0,
        active_duties_count=1,
        distance_meters=450.0,
    )
    profile_b = CandidateRankingProfile(
        driver=driver_b,
        address_familiarity_count=0,
        customer_familiarity_count=0,
        active_duties_count=1,
        distance_meters=2500.0,
    )

    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )

    engine = PriorityResolutionEngine()
    results = engine.rank_candidates(
        duty=ctx,
        candidates=[driver_b, driver_a],
        candidate_profiles=[profile_b, profile_a],
    )

    assert results[0].driver.id == driver_a.id
    assert results[0].distance_km < results[1].distance_km


def test_seniority_tie_breaker():
    """When all 4 tiers are tied, driver with earlier created_at (seniority) wins."""
    senior_date = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    junior_date = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    driver_senior = _make_candidate(name="Senior Driver", created_at=senior_date)
    driver_junior = _make_candidate(name="Junior Driver", created_at=junior_date)

    profile_senior = CandidateRankingProfile(
        driver=driver_senior,
        address_familiarity_count=1,
        customer_familiarity_count=1,
        active_duties_count=1,
        distance_meters=1000.0,
    )
    profile_junior = CandidateRankingProfile(
        driver=driver_junior,
        address_familiarity_count=1,
        customer_familiarity_count=1,
        active_duties_count=1,
        distance_meters=1000.0,
    )

    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )

    engine = PriorityResolutionEngine()
    results = engine.rank_candidates(
        duty=ctx,
        candidates=[driver_junior, driver_senior],
        candidate_profiles=[profile_junior, profile_senior],
    )

    assert results[0].driver.id == driver_senior.id


def test_id_tie_breaker():
    """When all 4 tiers and seniority are tied, smaller UUID string wins deterministically."""
    date_same = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    id_low = uuid.UUID("00000000-0000-0000-0000-000000000001")
    id_high = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

    driver_low = _make_candidate(name="Driver Low", created_at=date_same, driver_id=id_low)
    driver_high = _make_candidate(name="Driver High", created_at=date_same, driver_id=id_high)

    profile_low = CandidateRankingProfile(
        driver=driver_low,
        address_familiarity_count=0,
        customer_familiarity_count=0,
        active_duties_count=0,
        distance_meters=100.0,
    )
    profile_high = CandidateRankingProfile(
        driver=driver_high,
        address_familiarity_count=0,
        customer_familiarity_count=0,
        active_duties_count=0,
        distance_meters=100.0,
    )

    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )

    engine = PriorityResolutionEngine()
    results = engine.rank_candidates(
        duty=ctx,
        candidates=[driver_high, driver_low],
        candidate_profiles=[profile_high, profile_low],
    )

    assert results[0].driver.id == id_low


def test_empty_candidates_returns_empty():
    """Verify ranking an empty candidate list returns empty list."""
    ctx = DutyRankingContext(
        duty_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
    )
    engine = PriorityResolutionEngine()
    assert engine.rank_candidates(duty=ctx, candidates=[]) == []


def test_haversine_distance_accuracy():
    """Verify great-circle Haversine formula calculation accuracy."""
    # Bangalore MG Road (12.9756, 77.6066) to Indiranagar 100ft Road (12.9784, 77.6408)
    dist_km = haversine_distance(12.9756, 77.6066, 12.9784, 77.6408)
    assert 3.5 <= dist_km <= 4.0, f"Unexpected distance: {dist_km} km"

    # In meters:
    dist_m = haversine_distance_meters(12.9756, 77.6066, 12.9784, 77.6408)
    assert 3500.0 <= dist_m <= 4000.0

    # Same coordinates must return 0.0
    zero_dist = haversine_distance(12.9756, 77.6066, 12.9756, 77.6066)
    assert zero_dist == 0.0
