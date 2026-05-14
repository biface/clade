# =============================================================================
# tests/test_deletion.py — ADOPT on_delete callable tests.
#
# Validates the ADOPT deletion strategy on AdoptNode:
#   - Direct children are re-parented to grandparent.
#   - Paths are recalculated correctly after adoption.
#   - Root deletion makes children new roots.
#   - QuerySet.delete() produces the same result as instance.delete().
#   - ADOPT.deconstruct() returns the expected dotted path (migrations).
#
# Reference tree (AdoptNode):
#     A (root)
#     ├── B  ← will be deleted in most tests
#     │   ├── D
#     │   │   └── G
#     │   └── E
#     └── C
#
# Refs: DD-014 (#41), #43, #44, #49
# =============================================================================

import pytest

from clade.deletion import ADOPT
from tests.models import AdoptNode

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adopt_tree(db):
    """Reference tree using AdoptNode (on_delete=ADOPT).

    Mirrors the SimpleNode fixture in conftest.py but uses AdoptNode
    so that deletions trigger the ADOPT callable.
    """
    a = AdoptNode.objects.create(name="A")
    b = AdoptNode.objects.create(name="B", parent=a)
    c = AdoptNode.objects.create(name="C", parent=a)
    d = AdoptNode.objects.create(name="D", parent=b)
    e = AdoptNode.objects.create(name="E", parent=b)
    g = AdoptNode.objects.create(name="G", parent=d)

    for node in (a, b, c, d, e, g):
        node.refresh_from_db()

    return {"A": a, "B": b, "C": c, "D": d, "E": e, "G": g}


# ---------------------------------------------------------------------------
# ADOPT callable contract
# ---------------------------------------------------------------------------


class TestAdoptDeconstruct:
    """ADOPT.deconstruct() is required for Django migration serialisation."""

    def test_deconstruct_path(self):
        path, args, kwargs = ADOPT.deconstruct()
        assert path == "clade.deletion.ADOPT"
        assert args == []
        assert kwargs == {}


# ---------------------------------------------------------------------------
# Instance delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdoptInstanceDelete:
    """instance.delete() with on_delete=ADOPT re-parents children."""

    def test_children_adopted_by_grandparent(self, adopt_tree):
        """D and E are re-parented to A when B is deleted."""
        a, b, d, e = (
            adopt_tree["A"],
            adopt_tree["B"],
            adopt_tree["D"],
            adopt_tree["E"],
        )
        b.delete()

        d.refresh_from_db()
        e.refresh_from_db()
        assert d.parent_id == a.pk
        assert e.parent_id == a.pk

    def test_deleted_node_is_gone(self, adopt_tree):
        """Deleted node no longer exists in the database."""
        b = adopt_tree["B"]
        b.delete()
        assert not AdoptNode.objects.filter(pk=b.pk).exists()

    def test_no_orphan_after_adoption(self, adopt_tree):
        """No node is left without a valid parent reference."""
        adopt_tree["B"].delete()
        for node in AdoptNode.objects.all():
            if node.parent_id is not None:
                assert AdoptNode.objects.filter(pk=node.parent_id).exists()

    def test_paths_updated_after_adoption(self, adopt_tree):
        """D, E, and G have correct paths after B is adopted."""
        a, b, d, e, g = (
            adopt_tree["A"],
            adopt_tree["B"],
            adopt_tree["D"],
            adopt_tree["E"],
            adopt_tree["G"],
        )
        b.delete()

        d.refresh_from_db()
        e.refresh_from_db()
        g.refresh_from_db()

        assert d.path == f"{a.path}.{d.pk}"
        assert e.path == f"{a.path}.{e.pk}"
        assert g.path == f"{d.path}.{g.pk}"

    def test_root_deletion_makes_children_roots(self, adopt_tree):
        """Deleting a root node makes its children new roots."""
        a, b, c = adopt_tree["A"], adopt_tree["B"], adopt_tree["C"]
        a.delete()

        b.refresh_from_db()
        c.refresh_from_db()
        assert b.parent_id is None
        assert c.parent_id is None

    def test_root_deletion_updates_children_paths(self, adopt_tree):
        """Children of deleted root get new single-pk paths."""
        a, b, c = adopt_tree["A"], adopt_tree["B"], adopt_tree["C"]
        a.delete()

        b.refresh_from_db()
        c.refresh_from_db()
        assert b.path == str(b.pk)
        assert c.path == str(c.pk)


# ---------------------------------------------------------------------------
# QuerySet delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdoptQuerySetDelete:
    """QuerySet.delete() with on_delete=ADOPT produces the same result."""

    def test_queryset_delete_adopts_children(self, adopt_tree):
        """D and E are re-parented to A when B is deleted via QuerySet."""
        a, b, d, e = (
            adopt_tree["A"],
            adopt_tree["B"],
            adopt_tree["D"],
            adopt_tree["E"],
        )
        AdoptNode.objects.filter(pk=b.pk).delete()

        d.refresh_from_db()
        e.refresh_from_db()
        assert d.parent_id == a.pk
        assert e.parent_id == a.pk

    def test_queryset_delete_updates_paths(self, adopt_tree):
        """Paths are correct after QuerySet.delete() with ADOPT."""
        a, b, d, e, g = (
            adopt_tree["A"],
            adopt_tree["B"],
            adopt_tree["D"],
            adopt_tree["E"],
            adopt_tree["G"],
        )
        AdoptNode.objects.filter(pk=b.pk).delete()

        d.refresh_from_db()
        e.refresh_from_db()
        g.refresh_from_db()

        assert d.path == f"{a.path}.{d.pk}"
        assert e.path == f"{a.path}.{e.pk}"
        assert g.path == f"{d.path}.{g.pk}"
