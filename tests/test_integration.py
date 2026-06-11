# =============================================================================
# tests/test_integration.py — Parity tests: SQLite vs PostgreSQL backend.
#
# These tests run against a real PostgreSQL instance with the ltree extension
# enabled. They validate that NodeQuerySet produces identical results on
# PostgreSQL (native ltree operators) and SQLite (Django ORM fallback).
#
# Run with:
#   tox -e integration          (local — settings_integration_local.py)
#   tox -e integration-ci       (CI    — settings_integration.py + env var)
#
# Marker: @pytest.mark.integration
# Requires: PostgreSQL ≥ 14 with ltree extension, clade_test database.
#
# Refs: DD-003 (#3), DD-011 (#32), DD-013 (#40), DD-015
# =============================================================================

import pytest

from tests.models import SimpleNode


# =============================================================================
# Reference tree fixture
# =============================================================================
#
# Structure:
#   A (root)
#   ├── B
#   │   ├── D
#   │   │   └── G
#   │   └── E
#   └── C


@pytest.fixture
def pg_tree(db):
    """Reference tree on PostgreSQL — mirrors the SQLite fixture in conftest.py."""
    a = SimpleNode.objects.create(name="A")
    b = SimpleNode.objects.create(name="B", parent=a)
    c = SimpleNode.objects.create(name="C", parent=a)
    d = SimpleNode.objects.create(name="D", parent=b)
    e = SimpleNode.objects.create(name="E", parent=b)
    g = SimpleNode.objects.create(name="G", parent=d)

    for node in (a, b, c, d, e, g):
        node.refresh_from_db()

    return {"A": a, "B": b, "C": c, "D": d, "E": e, "G": g}


# =============================================================================
# Backend verification
# =============================================================================


@pytest.mark.integration
def test_postgresql_backend_active(db):
    """Confirm the active backend is PostgreSQL with ltree support."""
    from django.db import connection

    assert connection.vendor == "postgresql", (
        f"Expected postgresql backend, got {connection.vendor}. "
        "Check DJANGO_SETTINGS_MODULE."
    )


@pytest.mark.integration
def test_ltree_extension_enabled(db):
    """Confirm the ltree extension is installed on the test database."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'ltree';"
        )
        result = cursor.fetchone()

    assert result is not None, (
        "ltree extension is not enabled on clade_test. "
        "Run: CREATE EXTENSION IF NOT EXISTS ltree;"
    )


@pytest.mark.integration
def test_path_field_type_is_ltree(db):
    """Confirm CladeNode.path is stored as ltree on PostgreSQL."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'tests_simplenode'
              AND column_name = 'path';
            """
        )
        result = cursor.fetchone()

    assert result is not None, "Column path not found on tests_simplenode."
    assert result[0] == "USER-DEFINED", (
        f"Expected ltree (USER-DEFINED) column type, got {result[0]}."
    )


# =============================================================================
# Path maintenance parity
# =============================================================================


@pytest.mark.integration
def test_root_path_is_pk(db):
    """Root node path equals str(pk) on PostgreSQL."""
    node = SimpleNode.objects.create(name="root")
    node.refresh_from_db()
    assert node.path == str(node.pk)


@pytest.mark.integration
def test_child_path_is_parent_dot_pk(db):
    """Child path is parent.path + '.' + str(pk) on PostgreSQL."""
    root = SimpleNode.objects.create(name="root")
    root.refresh_from_db()
    child = SimpleNode.objects.create(name="child", parent=root)
    child.refresh_from_db()
    assert child.path == f"{root.path}.{child.pk}"


@pytest.mark.integration
def test_fixture_paths(pg_tree):
    """All fixture nodes carry the correct materialized paths on PostgreSQL."""
    t = pg_tree
    assert t["A"].path == str(t["A"].pk)
    assert t["B"].path == f"{t['A'].pk}.{t['B'].pk}"
    assert t["C"].path == f"{t['A'].pk}.{t['C'].pk}"
    assert t["D"].path == f"{t['A'].pk}.{t['B'].pk}.{t['D'].pk}"
    assert t["E"].path == f"{t['A'].pk}.{t['B'].pk}.{t['E'].pk}"
    assert t["G"].path == f"{t['A'].pk}.{t['B'].pk}.{t['D'].pk}.{t['G'].pk}"


# =============================================================================
# ancestors_of parity
# =============================================================================


@pytest.mark.integration
def test_ancestors_of_root_is_empty(pg_tree):
    """ancestors_of(root) returns empty QuerySet on PostgreSQL."""
    t = pg_tree
    assert not SimpleNode.objects.ancestors_of(t["A"]).exists()


@pytest.mark.integration
def test_ancestors_of_child(pg_tree):
    """ancestors_of(B) returns {A} on PostgreSQL."""
    t = pg_tree
    ancestors = set(SimpleNode.objects.ancestors_of(t["B"]))
    assert ancestors == {t["A"]}


@pytest.mark.integration
def test_ancestors_of_deep_node(pg_tree):
    """ancestors_of(G) returns {A, B, D} on PostgreSQL."""
    t = pg_tree
    ancestors = set(SimpleNode.objects.ancestors_of(t["G"]))
    assert ancestors == {t["A"], t["B"], t["D"]}


@pytest.mark.integration
def test_ancestors_ordered_by_path(pg_tree):
    """ancestors_of(G).order_by('path') returns [A, B, D] on PostgreSQL."""
    t = pg_tree
    ancestors = list(
        SimpleNode.objects.ancestors_of(t["G"]).order_by("path")
    )
    assert ancestors == [t["A"], t["B"], t["D"]]


# =============================================================================
# descendants_of parity
# =============================================================================


@pytest.mark.integration
def test_descendants_of_root(pg_tree):
    """descendants_of(A) returns all non-root nodes on PostgreSQL."""
    t = pg_tree
    descendants = set(SimpleNode.objects.descendants_of(t["A"]))
    assert descendants == {t["B"], t["C"], t["D"], t["E"], t["G"]}


@pytest.mark.integration
def test_descendants_of_leaf_is_empty(pg_tree):
    """descendants_of(G) returns empty QuerySet on PostgreSQL."""
    t = pg_tree
    assert not SimpleNode.objects.descendants_of(t["G"]).exists()


@pytest.mark.integration
def test_descendants_does_not_include_self(pg_tree):
    """descendants_of(B) does not include B itself on PostgreSQL."""
    t = pg_tree
    descendants = SimpleNode.objects.descendants_of(t["B"])
    assert t["B"] not in descendants


@pytest.mark.integration
def test_descendants_does_not_include_unrelated(pg_tree):
    """descendants_of(B) does not include C on PostgreSQL."""
    t = pg_tree
    descendants = SimpleNode.objects.descendants_of(t["B"])
    assert t["C"] not in descendants


# =============================================================================
# siblings_of parity
# =============================================================================


@pytest.mark.integration
def test_siblings_of_node_with_sibling(pg_tree):
    """siblings_of(B) returns {C} on PostgreSQL."""
    t = pg_tree
    siblings = set(SimpleNode.objects.siblings_of(t["B"]))
    assert siblings == {t["C"]}


@pytest.mark.integration
def test_siblings_excludes_self(pg_tree):
    """siblings_of(B) does not include B itself on PostgreSQL."""
    t = pg_tree
    siblings = SimpleNode.objects.siblings_of(t["B"])
    assert t["B"] not in siblings


@pytest.mark.integration
def test_siblings_of_only_child_is_empty(pg_tree):
    """siblings_of(C) returns empty QuerySet (C is the only child of A
    after B) — actually C has sibling B, so test the leaf G instead."""
    t = pg_tree
    assert not SimpleNode.objects.siblings_of(t["G"]).exists()


@pytest.mark.integration
def test_siblings_of_root_is_empty(pg_tree):
    """siblings_of(A) returns empty QuerySet on PostgreSQL."""
    t = pg_tree
    assert not SimpleNode.objects.siblings_of(t["A"]).exists()


# =============================================================================
# root_of parity
# =============================================================================


@pytest.mark.integration
def test_root_of_deep_node(pg_tree):
    """root_of(G) returns A on PostgreSQL."""
    t = pg_tree
    root_qs = SimpleNode.objects.root_of(t["G"])
    assert root_qs.get() == t["A"]


@pytest.mark.integration
def test_root_of_root_is_self(pg_tree):
    """root_of(A) returns A itself on PostgreSQL."""
    t = pg_tree
    root_qs = SimpleNode.objects.root_of(t["A"])
    assert root_qs.get() == t["A"]


# =============================================================================
# Instance methods parity
# =============================================================================


@pytest.mark.integration
def test_instance_ancestors_delegates(pg_tree):
    """node.ancestors() delegates to NodeQuerySet on PostgreSQL."""
    t = pg_tree
    assert set(t["G"].ancestors()) == {t["A"], t["B"], t["D"]}


@pytest.mark.integration
def test_instance_descendants_delegates(pg_tree):
    """node.descendants() delegates to NodeQuerySet on PostgreSQL."""
    t = pg_tree
    assert set(t["B"].descendants()) == {t["D"], t["E"], t["G"]}


@pytest.mark.integration
def test_is_root_true_for_root(pg_tree):
    """is_root is True for the root node on PostgreSQL."""
    assert pg_tree["A"].is_root is True


@pytest.mark.integration
def test_is_root_false_for_non_root(pg_tree):
    """is_root is False for non-root nodes on PostgreSQL."""
    assert pg_tree["B"].is_root is False


@pytest.mark.integration
def test_is_leaf_true_for_leaves(pg_tree):
    """is_leaf is True for leaf nodes on PostgreSQL."""
    t = pg_tree
    assert t["G"].is_leaf is True
    assert t["C"].is_leaf is True
    assert t["E"].is_leaf is True


@pytest.mark.integration
def test_is_leaf_false_for_internal(pg_tree):
    """is_leaf is False for internal nodes on PostgreSQL."""
    t = pg_tree
    assert t["A"].is_leaf is False
    assert t["B"].is_leaf is False
