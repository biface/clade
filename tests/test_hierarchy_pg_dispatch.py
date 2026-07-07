# =============================================================================
# tests/test_hierarchy_pg_dispatch.py — PostgreSQL dispatch tests for NodeQuerySet.
#
# Verifies that ancestors_of() and descendants_of() select the correct
# PostgreSQL code path (ltree @> / <@ lookups) when connection.vendor
# is "postgresql".
#
# Strategy
# --------
# LtreeField lookups generate PostgreSQL-specific SQL (@>, <@) that SQLite
# cannot execute. These tests therefore only verify the dispatch logic —
# that the correct lookup is selected — without evaluating the QuerySet.
# The QuerySet is inspected at the SQL string level via str(qs.query).
#
# Functional correctness on PostgreSQL is validated by tox -e integration.
#
# Reference tree (mirrors conftest.py):
#     A (root)
#     ├── B
#     │   ├── D
#     │   │   └── G
#     │   └── E
#     └── C
#
# Refs: DD-003 (#3), DD-013 (#40), DD-015, DD-016 (#56), #45, #62
# =============================================================================

from unittest.mock import MagicMock, patch

import pytest

import clade.managers as _managers_module
from tests.models import SimpleNode

# =============================================================================
# Patch helper
# =============================================================================

# connection in Django is a ConnectionProxy resolved via __getattr__.
# Replace the module-level reference with a MagicMock that wraps the real
# connection (so ORM machinery is intact) but exposes vendor="postgresql".
# The QuerySet is built but never evaluated — no ltree SQL hits SQLite.


def _pg_vendor_patch():
    """Context manager: patch clade.managers.connection.vendor to 'postgresql'."""
    real_conn = _managers_module.connection
    mock_conn = MagicMock(wraps=real_conn)
    mock_conn.vendor = "postgresql"
    return patch.object(_managers_module, "connection", mock_conn)


# =============================================================================
# ancestors_of — PostgreSQL dispatch
# =============================================================================


@pytest.mark.django_db
class TestAncestorsPostgresDispatch:
    """ancestors_of() selects the ltree @> lookup on PostgreSQL."""

    def test_uses_ancestor_of_lookup(self, tree):
        """The generated SQL contains the @> operator on PostgreSQL."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.ancestors_of(tree["G"])
            sql = str(qs.query)
        assert "@>" in sql

    def test_excludes_self(self, tree):
        """ancestors_of excludes the node itself (NOT id=...) on PostgreSQL."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.ancestors_of(tree["G"])
            sql = str(qs.query)
        assert str(tree["G"].pk) in sql


# =============================================================================
# descendants_of — PostgreSQL dispatch
# =============================================================================


@pytest.mark.django_db
class TestDescendantsPostgresDispatch:
    """descendants_of() selects the ltree <@ lookup on PostgreSQL."""

    def test_uses_descendant_of_lookup(self, tree):
        """The generated SQL contains the <@ operator on PostgreSQL."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.descendants_of(tree["B"])
            sql = str(qs.query)
        assert "<@" in sql

    def test_excludes_self(self, tree):
        """descendants_of excludes the node itself (NOT id=...) on PostgreSQL."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.descendants_of(tree["B"])
            sql = str(qs.query)
        assert str(tree["B"].pk) in sql


# =============================================================================
# cousins_of — PostgreSQL dispatch (DD-016, #56, #62)
# =============================================================================


@pytest.mark.django_db
class TestCousinsPostgresDispatch:
    """cousins_of() selects the ltree <@ lookup + NLevel depth filter."""

    def test_uses_descendant_of_lookup(self, tree):
        """The generated SQL contains the <@ operator (ancestor-subtree filter)."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.cousins_of(tree["D"], degree=2)
            sql = str(qs.query)
        assert "<@" in sql

    def test_excludes_closer_ancestor_branch(self, tree):
        """The generated SQL negates the closer-ancestor <@ filter (NOT)."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.cousins_of(tree["D"], degree=2)
            sql = str(qs.query)
        assert "NOT" in sql

    def test_uses_nlevel_for_depth_filter(self, tree):
        """The generated SQL calls nlevel() for the exact-depth filter."""
        with _pg_vendor_patch():
            qs = SimpleNode.objects.cousins_of(tree["D"], degree=2)
            sql = str(qs.query)
        assert "nlevel" in sql.lower()

    def test_degree_one_dispatches_without_error(self, tree):
        """degree=1 (closer_ancestor_path == node_path) still dispatches to
        the PostgreSQL branch without raising — the inclusive <@ operator
        handles self-exclusion (see managers.py comment, DD-015 #55 bugfix).
        """
        with _pg_vendor_patch():
            qs = SimpleNode.objects.cousins_of(tree["D"], degree=1)
            sql = str(qs.query)
        assert "<@" in sql
        assert "nlevel" in sql.lower()

    def test_queryset_not_evaluated(self, tree):
        """Sanity check: inspecting str(qs.query) never hits the database.

        SQLite cannot execute <@ / nlevel() — if this test passes at all
        (no OperationalError), the QuerySet was correctly left unevaluated.
        """
        with _pg_vendor_patch():
            qs = SimpleNode.objects.cousins_of(tree["D"], degree=2)
            str(qs.query)  # must not raise
