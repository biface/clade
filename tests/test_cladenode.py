# =============================================================================
# tests/test_cladenode.py — CladeNode structural tests
#
# Validates that CladeNode is correctly wired as an abstract model
# and that concrete subclasses behave as expected.
#
# Scope of this file
# ------------------
# - Basic CRUD on SimpleNode (no path maintenance required)
# - Parent/children FK relationship
# - path field existence (value populated by signal #44)
#
# Out of scope here (separate test files, later issues)
# - Path value correctness    → test_path.py       (#44, #48)
# - Hierarchy query methods   → test_hierarchy.py  (#45, #48)
# - ADOPT deletion strategy   → test_deletion.py   (#43, #49)
#
# Refs: DD-012
#   https://gitlab.com/open-works/clade/-/issues/39  (DD-012)
#   https://gitlab.com/open-works/clade/-/issues/42  (CladeNode structure)
#   https://gitlab.com/open-works/clade/-/issues/48  (hierarchy tests)
#   https://gitlab.com/open-works/clade/-/issues/50  (CI workaround removal)
# =============================================================================

import pytest

from tests.models import SimpleNode


@pytest.mark.django_db
class TestCladeNodeStructure:
    """CladeNode as an abstract base — structural validation."""

    # ── Creation ──────────────────────────────────────────────────────────────

    def test_root_node_creation(self):
        """A root node (no parent) can be created."""
        node = SimpleNode.objects.create(name="root")
        assert node.pk is not None
        assert node.parent is None
        assert node.parent_id is None

    def test_child_node_creation(self):
        """A child node can be created with a parent reference."""
        root = SimpleNode.objects.create(name="root")
        child = SimpleNode.objects.create(name="child", parent=root)
        assert child.parent_id == root.pk

    def test_grandchild_node_creation(self):
        """Nodes can be nested to arbitrary depth."""
        root = SimpleNode.objects.create(name="root")
        child = SimpleNode.objects.create(name="child", parent=root)
        grandchild = SimpleNode.objects.create(name="grandchild", parent=child)
        assert grandchild.parent_id == child.pk

    # ── Relationships ─────────────────────────────────────────────────────────

    def test_children_related_manager(self):
        """Parent exposes direct children via the children related manager."""
        root = SimpleNode.objects.create(name="root")
        c1 = SimpleNode.objects.create(name="c1", parent=root)
        c2 = SimpleNode.objects.create(name="c2", parent=root)
        child_pks = set(root.children.values_list("pk", flat=True))
        assert child_pks == {c1.pk, c2.pk}

    def test_unrelated_node_not_in_children(self):
        """A node with a different parent is not a child of root."""
        root = SimpleNode.objects.create(name="root")
        other = SimpleNode.objects.create(name="other")
        assert other.pk not in root.children.values_list("pk", flat=True)

    # ── Path field ────────────────────────────────────────────────────────────

    def test_path_field_exists(self):
        """The path field is present on every CladeNode instance."""
        node = SimpleNode.objects.create(name="root")
        assert hasattr(node, "path")

    def test_path_field_is_string(self):
        """The path field is a string (populated by signal #44)."""
        node = SimpleNode.objects.create(name="root")
        node.refresh_from_db()
        assert isinstance(node.path, str)

    # ── Meta ──────────────────────────────────────────────────────────────────

    def test_default_ordering_by_path(self):
        """Default queryset ordering is by path (consistent depth-first)."""
        assert SimpleNode._meta.ordering == ["path"]

    def test_cladenode_is_abstract(self):
        """CladeNode itself has no database table."""
        from clade.models import CladeNode

        assert CladeNode._meta.abstract is True
