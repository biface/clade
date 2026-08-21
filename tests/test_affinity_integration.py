# =============================================================================
# tests/test_affinity_integration.py — Parity tests: Affinity on PostgreSQL.
#
# Mirrors tests/test_affinity.py (SQLite) against a real PostgreSQL instance.
# Affinity introduces no backend-specific DDL or query dispatch — the
# migration (clade/migrations/0001_affinity.py) is identical on every
# backend (ContentType FKs + CharFields only, no LtreeField or
# ConditionalAlterField involved, unlike the tree/kinship parity tests in
# test_integration.py). These tests exist to confirm that observation
# empirically rather than leave it merely asserted in a comment.
#
# clade.E001/E002 (TestAffinityChecks in test_affinity.py) are deliberately
# NOT mirrored here — django.core.checks validate Meta.affinity_rules in
# pure Python, no database access involved, so duplicating them against
# PostgreSQL would test nothing that SQLite doesn't already cover.
#
# Run with:
#   tox -e integration          (local — settings_integration_local.py)
#   tox -e integration-ci       (CI    — settings_integration.py + env var)
#
# Marker: @pytest.mark.integration
# Requires: PostgreSQL ≥ 14, clade_test database (ltree not required by
# Affinity itself, but already enabled for the tree/kinship parity suite).
#
# Refs: DD-005 (#5), DD-011 (#32), #74
# =============================================================================

import pytest

from clade.affinity import (
    Affinity,
    HeterogeneousAffinityError,
    affinities_of,
    affinities_of_grouped,
)
from tests.models import AffinityDepartment, AffinityDepartmentAlt, AffinityProject


def _pairs(channel=None):
    """Return {(side_a, side_b)} for readable assertions, optionally
    filtered to one channel."""
    qs = Affinity.objects.all()
    if channel is not None:
        qs = qs.filter(channel=channel)
    return {(a.side_a, a.side_b) for a in qs}


# =============================================================================
# Source-side trigger
# =============================================================================


@pytest.mark.integration
def test_source_save_creates_matching_rows(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris", lead="alice")
    p2 = AffinityProject.objects.create(title="P2", cost_center="paris", lead="bob")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris", manager="alice")

    assert _pairs("geo") == {(d1, p1), (d1, p2)}
    assert _pairs("management") == {(d1, p1)}


@pytest.mark.integration
def test_source_save_with_no_match_creates_nothing(db):
    AffinityProject.objects.create(title="P1", cost_center="lyon")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")

    assert not Affinity.objects.filter(object_id_a=d1.pk).exists()


@pytest.mark.integration
def test_null_local_field_creates_nothing(db):
    """A None value never matches — not even another None (DD-005)."""
    AffinityProject.objects.create(title="P1", cost_center=None)
    d1 = AffinityDepartment.objects.create(name="D1", region=None)

    assert not Affinity.objects.filter(object_id_a=d1.pk, channel="geo").exists()


@pytest.mark.integration
def test_source_value_change_replaces_stale_rows(db):
    p_paris = AffinityProject.objects.create(title="P-paris", cost_center="paris")
    p_lyon = AffinityProject.objects.create(title="P-lyon", cost_center="lyon")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    assert _pairs("geo") == {(d1, p_paris)}

    d1.region = "lyon"
    d1.save()

    assert _pairs("geo") == {(d1, p_lyon)}


# =============================================================================
# Target-side trigger (bidirectional registry — DD-005)
# =============================================================================


@pytest.mark.integration
def test_target_save_after_source_creates_row(db):
    """Reverse-index trigger: no AffinityDepartment save involved."""
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    assert not Affinity.objects.filter(channel="geo").exists()

    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")

    assert _pairs("geo") == {(d1, p1)}


@pytest.mark.integration
def test_target_value_change_replaces_stale_rows(db):
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    assert _pairs("geo") == {(d1, p1)}

    p1.cost_center = "lyon"
    p1.save()

    assert not Affinity.objects.filter(channel="geo").exists()


@pytest.mark.integration
def test_target_null_value_creates_nothing(db):
    AffinityDepartment.objects.create(name="D1", region="paris")
    p1 = AffinityProject.objects.create(title="P1", cost_center=None)

    assert not Affinity.objects.filter(object_id_b=p1.pk, channel="geo").exists()


# =============================================================================
# Cross-source channel-name collision
# =============================================================================


@pytest.mark.integration
def test_cross_source_same_channel_no_wipeout(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    d2 = AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

    assert _pairs("geo") == {(d1, p1), (d2, p1)}

    # Re-saving p1 (target-side resync for BOTH rules) must not drop
    # either source's row.
    p1.save()

    assert _pairs("geo") == {(d1, p1), (d2, p1)}


# =============================================================================
# Deletion — purges both sides, regardless of channel
# =============================================================================


@pytest.mark.integration
def test_deleting_source_purges_its_rows(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris", lead="alice")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris", manager="alice")
    assert Affinity.objects.count() == 2

    d1.delete()

    assert Affinity.objects.count() == 0


@pytest.mark.integration
def test_deleting_target_purges_referencing_rows(db):
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    assert Affinity.objects.count() == 1

    p1.delete()

    assert Affinity.objects.count() == 0


@pytest.mark.integration
def test_deleting_one_of_several_targets_keeps_the_others(db):
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    p2 = AffinityProject.objects.create(title="P2", cost_center="paris")
    assert _pairs("geo") == {(d1, p1), (d1, p2)}

    p1.delete()

    assert _pairs("geo") == {(d1, p2)}


# =============================================================================
# affinities_of() — homogeneous case
# =============================================================================


@pytest.mark.integration
def test_source_side_returns_typed_queryset_of_target_model(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    p2 = AffinityProject.objects.create(title="P2", cost_center="paris")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")

    result = affinities_of(d1, channel="geo")

    assert result.model is AffinityProject
    assert set(result) == {p1, p2}


@pytest.mark.integration
def test_target_side_returns_typed_queryset_of_source_model(db):
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")

    result = affinities_of(p1, channel="geo")

    assert result.model is AffinityDepartment
    assert set(result) == {d1}


@pytest.mark.integration
def test_no_matching_rows_returns_empty_typed_queryset(db):
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")

    result = affinities_of(d1, channel="geo")

    assert result.model is AffinityProject
    assert not result.exists()


@pytest.mark.integration
def test_instance_method_delegates(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")

    assert set(d1.affinities(channel="geo")) == set(affinities_of(d1, channel="geo"))


# =============================================================================
# affinities_of() / affinities_of_grouped() — heterogeneous case
# =============================================================================


@pytest.mark.integration
def test_raises_when_two_source_models_share_channel(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    AffinityDepartment.objects.create(name="D1", region="paris")
    AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

    with pytest.raises(HeterogeneousAffinityError):
        affinities_of(p1, channel="geo")


@pytest.mark.integration
def test_grouped_never_raises_and_splits_by_model(db):
    p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
    d1 = AffinityDepartment.objects.create(name="D1", region="paris")
    d2 = AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

    result = affinities_of_grouped(p1, channel="geo")

    assert set(result.keys()) == {AffinityDepartment, AffinityDepartmentAlt}
    assert set(result[AffinityDepartment]) == {d1}
    assert set(result[AffinityDepartmentAlt]) == {d2}
