# =============================================================================
# tests/test_path.py — Path maintenance tests.
#
# Validates that the post_save signal correctly maintains the ``path``
# field on CladeNode subclasses for all write operations.
#
# Refs: DD-013 (#40), #44, #48
# =============================================================================

import pytest

from tests.models import SimpleNode


@pytest.mark.django_db
class TestPathMaintenance:
    """post_save signal maintains path on create, child create, reparent."""

    # ── Creation ──────────────────────────────────────────────────────────────

    def test_root_path_is_pk(self):
        """Root node path equals str(pk)."""
        node = SimpleNode.objects.create(name="root")
        node.refresh_from_db()
        assert node.path == str(node.pk)

    def test_child_path_is_parent_dot_pk(self):
        """Child path is parent.path + '.' + str(pk)."""
        root = SimpleNode.objects.create(name="root")
        root.refresh_from_db()
        child = SimpleNode.objects.create(name="child", parent=root)
        child.refresh_from_db()
        assert child.path == f"{root.path}.{child.pk}"

    def test_grandchild_path(self):
        """Grandchild path extends the parent chain."""
        root = SimpleNode.objects.create(name="root")
        root.refresh_from_db()
        child = SimpleNode.objects.create(name="child", parent=root)
        child.refresh_from_db()
        grandchild = SimpleNode.objects.create(name="grandchild", parent=child)
        grandchild.refresh_from_db()
        assert grandchild.path == f"{child.path}.{grandchild.pk}"

    def test_path_populated_before_save_returns(self):
        """path is set on the in-memory instance after create()."""
        node = SimpleNode.objects.create(name="root")
        assert node.path == str(node.pk)

    # ── Reference fixture ─────────────────────────────────────────────────────

    def test_fixture_paths(self, tree):
        """Reference tree has correct paths for all nodes."""
        a, b, c, d, e, g = (
            tree["A"],
            tree["B"],
            tree["C"],
            tree["D"],
            tree["E"],
            tree["G"],
        )
        assert a.path == str(a.pk)
        assert b.path == f"{a.path}.{b.pk}"
        assert c.path == f"{a.path}.{c.pk}"
        assert d.path == f"{b.path}.{d.pk}"
        assert e.path == f"{b.path}.{e.pk}"
        assert g.path == f"{d.path}.{g.pk}"

    # ── Reparent ──────────────────────────────────────────────────────────────

    def test_reparent_updates_node_path(self):
        """Moving a node updates its own path."""
        root = SimpleNode.objects.create(name="root")
        root.refresh_from_db()
        other = SimpleNode.objects.create(name="other")
        other.refresh_from_db()
        child = SimpleNode.objects.create(name="child", parent=root)
        child.refresh_from_db()

        # Move child from root to other
        child.parent = other
        child.save()
        child.refresh_from_db()
        assert child.path == f"{other.path}.{child.pk}"

    def test_reparent_cascades_to_descendants(self):
        """Moving a node updates all descendant paths."""
        root = SimpleNode.objects.create(name="root")
        root.refresh_from_db()
        other = SimpleNode.objects.create(name="other")
        other.refresh_from_db()
        child = SimpleNode.objects.create(name="child", parent=root)
        child.refresh_from_db()
        grandchild = SimpleNode.objects.create(name="grandchild", parent=child)
        grandchild.refresh_from_db()

        old_grandchild_suffix = grandchild.path[len(child.path) :]

        child.parent = other
        child.save()
        child.refresh_from_db()
        grandchild.refresh_from_db()

        expected = child.path + old_grandchild_suffix
        assert grandchild.path == expected
