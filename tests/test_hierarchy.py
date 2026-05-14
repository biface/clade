# =============================================================================
# tests/test_hierarchy.py — Hierarchy query method tests.
#
# Validates NodeQuerySet and CladeNode instance methods against the
# reference tree fixture defined in tests/conftest.py.
#
# Reference tree:
#     A (root)
#     ├── B
#     │   ├── D
#     │   │   └── G
#     │   └── E
#     └── C
#
# Refs: DD-002 (#2), DD-013 (#40), #45, #46, #48
# =============================================================================

import pytest

from tests.models import SimpleNode


@pytest.mark.django_db
class TestAncestors:
    """ancestors_of() and node.ancestors()"""

    def test_ancestors_of_child(self, tree):
        """Direct child has exactly one ancestor — the root."""
        result = set(SimpleNode.objects.ancestors_of(tree["B"]))
        assert result == {tree["A"]}

    def test_ancestors_of_deep_node(self, tree):
        """Deep node has all nodes on path to root as ancestors."""
        result = set(SimpleNode.objects.ancestors_of(tree["G"]))
        assert result == {tree["A"], tree["B"], tree["D"]}

    def test_ancestors_of_root_is_empty(self, tree):
        """Root node has no ancestors."""
        assert not SimpleNode.objects.ancestors_of(tree["A"]).exists()

    def test_ancestors_ordered_by_path(self, tree):
        """ancestors_of returns nodes in root-first order when ordered."""
        ordered = list(SimpleNode.objects.ancestors_of(tree["G"]).order_by("path"))
        assert ordered == [tree["A"], tree["B"], tree["D"]]

    def test_instance_ancestors_delegates(self, tree):
        """node.ancestors() returns same QuerySet as ancestors_of(node)."""
        qs_manager = set(SimpleNode.objects.ancestors_of(tree["G"]))
        qs_instance = set(tree["G"].ancestors())
        assert qs_manager == qs_instance


@pytest.mark.django_db
class TestDescendants:
    """descendants_of() and node.descendants()"""

    def test_descendants_of_node_with_subtree(self, tree):
        """Node with a subtree returns all descendants."""
        result = set(SimpleNode.objects.descendants_of(tree["B"]))
        assert result == {tree["D"], tree["E"], tree["G"]}

    def test_descendants_of_leaf_is_empty(self, tree):
        """Leaf node has no descendants."""
        assert not SimpleNode.objects.descendants_of(tree["G"]).exists()

    def test_descendants_does_not_include_self(self, tree):
        """descendants_of does not include the node itself."""
        result = SimpleNode.objects.descendants_of(tree["B"])
        assert tree["B"] not in result

    def test_descendants_does_not_include_unrelated(self, tree):
        """descendants_of does not include nodes outside the subtree."""
        result = SimpleNode.objects.descendants_of(tree["B"])
        assert tree["C"] not in result

    def test_instance_descendants_delegates(self, tree):
        """node.descendants() returns same QuerySet as descendants_of(node)."""
        qs_manager = set(SimpleNode.objects.descendants_of(tree["B"]))
        qs_instance = set(tree["B"].descendants())
        assert qs_manager == qs_instance


@pytest.mark.django_db
class TestSiblings:
    """siblings_of() and node.siblings()"""

    def test_siblings_of_node_with_sibling(self, tree):
        """Node with a sibling returns that sibling."""
        result = set(SimpleNode.objects.siblings_of(tree["B"]))
        assert result == {tree["C"]}

    def test_siblings_excludes_self(self, tree):
        """siblings_of does not include the node itself."""
        result = SimpleNode.objects.siblings_of(tree["B"])
        assert tree["B"] not in result

    def test_siblings_of_only_child_is_empty(self, tree):
        """Only-child node (unique child of its parent) has no siblings."""
        assert not SimpleNode.objects.siblings_of(tree["G"]).exists()

    def test_siblings_of_root_is_empty(self, tree):
        """Root node has no siblings (no parent)."""
        assert not SimpleNode.objects.siblings_of(tree["A"]).exists()

    def test_instance_siblings_delegates(self, tree):
        """node.siblings() returns same QuerySet as siblings_of(node)."""
        qs_manager = set(SimpleNode.objects.siblings_of(tree["B"]))
        qs_instance = set(tree["B"].siblings())
        assert qs_manager == qs_instance


@pytest.mark.django_db
class TestRoot:
    """root_of() and node.root property"""

    def test_root_of_deep_node(self, tree):
        """Deep node returns the tree root."""
        result = SimpleNode.objects.root_of(tree["G"]).get()
        assert result == tree["A"]

    def test_root_of_root_is_self(self, tree):
        """Root node returns itself."""
        result = SimpleNode.objects.root_of(tree["A"]).get()
        assert result == tree["A"]

    def test_root_property(self, tree):
        """node.root returns the root node."""
        assert tree["G"].root == tree["A"]
        assert tree["A"].root == tree["A"]


@pytest.mark.django_db
class TestIsRootIsLeaf:
    """is_root and is_leaf properties"""

    def test_is_root_true_for_root(self, tree):
        assert tree["A"].is_root is True

    def test_is_root_false_for_non_root(self, tree):
        for name in ("B", "C", "D", "E", "G"):
            assert tree[name].is_root is False, f"{name} should not be root"

    def test_is_leaf_true_for_leaves(self, tree):
        for name in ("C", "E", "G"):
            assert tree[name].is_leaf is True, f"{name} should be a leaf"

    def test_is_leaf_false_for_internal(self, tree):
        for name in ("A", "B", "D"):
            assert tree[name].is_leaf is False, f"{name} should not be a leaf"
