# =============================================================================
# tests/test_affinity_transitivity_integration.py — Parity tests: DD-018
# closure engine and invalidation on PostgreSQL.
#
# Mirrors tests/test_affinity_transitivity.py (SQLite) against a real
# PostgreSQL instance. The closure engine and invalidation wiring
# introduce no backend-specific DDL or query dispatch — the self-join is
# plain Python over ContentType/object_id tuples, and Affinity.is_derived
# is an ordinary BooleanField (#89) — so, exactly like #74's parity suite
# for direct Affinity rows, this exists to confirm that observation
# empirically rather than leave it merely asserted in a comment.
#
# clade.E003 (TestAffinityE003 in test_affinity.py) is deliberately NOT
# mirrored here, for the same reason clade.E001/E002 aren't mirrored in
# test_affinity_integration.py — django.core.checks validates
# Meta.affinity_rules in pure Python, no database access involved.
#
# Run with:
#   tox -e integration          (local — settings_integration_local.py)
#   tox -e integration-ci       (CI    — settings_integration.py + env var)
#
# Marker: @pytest.mark.integration
# Requires: PostgreSQL >= 14, clade_test database (ltree not required by
# Affinity itself, but already enabled for the tree/kinship parity suite).
#
# Refs: DD-018 (#88), #92, #93, #97
# =============================================================================

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from clade.affinity import Affinity, _recompute_shared_closure
from tests.models import (
    AffinityChainA,
    AffinityChainB,
    AffinityChainC,
    AffinityChainD,
    AffinityDepartment,
    AffinityDepartmentAlt,
    AffinityProject,
)


def _ct(model):
    return ContentType.objects.get_for_model(model)


def _pair_exists(a, b, channel, is_derived=None):
    ct_a, ct_b = _ct(type(a)), _ct(type(b))
    qs = Affinity.objects.filter(
        Q(
            content_type_a=ct_a,
            object_id_a=a.pk,
            content_type_b=ct_b,
            object_id_b=b.pk,
        )
        | Q(
            content_type_a=ct_b,
            object_id_a=b.pk,
            content_type_b=ct_a,
            object_id_b=a.pk,
        ),
        channel=channel,
    )
    if is_derived is not None:
        qs = qs.filter(is_derived=is_derived)
    return qs.exists()


def _all_pairs(channel):
    """{frozenset({a_key, b_key}): is_derived} for every row under
    *channel*, keyed by (content_type_id, object_id)."""
    result = {}
    for row in Affinity.objects.filter(channel=channel):
        a = (row.content_type_a_id, row.object_id_a)
        b = (row.content_type_b_id, row.object_id_b)
        result[frozenset((a, b))] = row.is_derived
    return result


# =============================================================================
# Closure correctness (#95 parity)
# =============================================================================


@pytest.mark.integration
def test_two_hop_chain_produces_exact_derived_set(db):
    p = AffinityProject.objects.create(title="P", cost_center="west")
    d = AffinityDepartment.objects.create(name="D", region="west")
    s = AffinityDepartmentAlt.objects.create(name="S", zone="west")

    assert _pair_exists(d, p, "geo", is_derived=False)
    assert _pair_exists(s, p, "geo", is_derived=False)
    assert _pair_exists(d, s, "geo", is_derived=True)

    pairs = _all_pairs("geo")
    assert len(pairs) == 3
    assert list(pairs.values()).count(True) == 1


@pytest.mark.integration
def test_ring_closes_into_complete_graph(db):
    a = AffinityChainA.objects.create(v="west")
    b = AffinityChainB.objects.create(v="west")
    c = AffinityChainC.objects.create(v="west")
    d = AffinityChainD.objects.create(v="west")

    for x, y in [(a, b), (b, c), (c, d), (d, a)]:
        assert _pair_exists(x, y, "chain", is_derived=False)

    assert _pair_exists(a, c, "chain", is_derived=True)
    assert _pair_exists(b, d, "chain", is_derived=True)

    pairs = _all_pairs("chain")
    assert len(pairs) == 6
    assert list(pairs.values()).count(True) == 2
    assert list(pairs.values()).count(False) == 4


@pytest.mark.integration
def test_mismatched_value_at_pivot_produces_no_derived_row(db):
    d = AffinityDepartment.objects.create(name="D")
    p = AffinityProject.objects.create(title="P")
    s = AffinityDepartmentAlt.objects.create(name="S")

    ct_d, ct_p, ct_s = (
        _ct(AffinityDepartment),
        _ct(AffinityProject),
        _ct(AffinityDepartmentAlt),
    )
    Affinity.objects.create(
        content_type_a=ct_d,
        object_id_a=d.pk,
        content_type_b=ct_p,
        object_id_b=p.pk,
        channel="geo",
        value="west",
    )
    Affinity.objects.create(
        content_type_a=ct_p,
        object_id_a=p.pk,
        content_type_b=ct_s,
        object_id_b=s.pk,
        channel="geo",
        value="east",
    )

    created = _recompute_shared_closure("geo")

    assert created == 0
    assert not _pair_exists(d, s, "geo")


@pytest.mark.integration
def test_rerunning_closure_creates_nothing_new(db):
    AffinityChainA.objects.create(v="west")
    AffinityChainB.objects.create(v="west")
    AffinityChainC.objects.create(v="west")
    AffinityChainD.objects.create(v="west")

    pairs_before = _all_pairs("chain")
    assert len(pairs_before) == 6

    created = _recompute_shared_closure("chain")

    assert created == 0
    assert _all_pairs("chain") == pairs_before
    assert _recompute_shared_closure("chain") == 0


# =============================================================================
# Invalidation (#96 parity)
# =============================================================================


@pytest.mark.integration
def test_deleting_sole_bridge_removes_derived_pair(db):
    d = AffinityDepartment.objects.create(name="D", region="west")
    p = AffinityProject.objects.create(title="P", cost_center="west")
    s = AffinityDepartmentAlt.objects.create(name="S", zone="west")

    assert _pair_exists(d, s, "geo", is_derived=True)

    p.delete()

    assert not _pair_exists(d, s, "geo")


@pytest.mark.integration
def test_deleting_bridge_with_alternate_path_recreates_pair(db):
    a = AffinityChainA.objects.create(v="west")
    b = AffinityChainB.objects.create(v="west")
    c = AffinityChainC.objects.create(v="west")
    AffinityChainD.objects.create(v="west")

    assert _pair_exists(a, c, "chain", is_derived=True)

    b.delete()

    assert not _pair_exists(a, b, "chain")
    assert not _pair_exists(b, c, "chain")
    assert _pair_exists(a, c, "chain", is_derived=True)


@pytest.mark.integration
def test_value_change_away_from_shared_value_removes_derived_pair(db):
    d = AffinityDepartment.objects.create(name="D", region="west")
    p = AffinityProject.objects.create(title="P", cost_center="west")
    s = AffinityDepartmentAlt.objects.create(name="S", zone="west")

    assert _pair_exists(d, s, "geo", is_derived=True)

    p.cost_center = "lyon"
    p.save()

    assert not _pair_exists(d, p, "geo")
    assert not _pair_exists(s, p, "geo")
    assert not _pair_exists(d, s, "geo")


@pytest.mark.integration
def test_value_change_to_match_different_chain_produces_new_pair(db):
    d = AffinityDepartment.objects.create(name="D", region="west")
    p = AffinityProject.objects.create(title="P", cost_center="west")
    s_west = AffinityDepartmentAlt.objects.create(name="S-west", zone="west")
    s_east = AffinityDepartmentAlt.objects.create(name="S-east", zone="east")

    assert _pair_exists(d, s_west, "geo", is_derived=True)
    assert not _pair_exists(d, s_east, "geo")

    d.region = "east"
    p.cost_center = "east"
    d.save()
    p.save()

    assert not _pair_exists(d, s_west, "geo")
    assert _pair_exists(d, s_east, "geo", is_derived=True)
