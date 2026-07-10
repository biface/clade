# =============================================================================
# tests/test_kinship_extended.py — pibling / nibling / cousin query tests.
#
# Validates NodeQuerySet.piblings_of/niblings_of/cousins_of, NodeManager
# proxies, and CladeNode instance methods against the kinship_tree fixture
# defined in tests/conftest.py.
#
# Reference tree:
#     A (root)
#     ├── B
#     │   ├── D
#     │   │   └── G
#     │   └── E
#     └── C
#         └── F
#
# Refs: DD-002 (#2), DD-016 (#56), #58, #59, #60, #61
# =============================================================================

import pytest

from tests.models import SimpleNode


@pytest.mark.django_db
class TestPiblings:
    """piblings_of() and node.piblings()"""

    def test_piblings_of_node_with_pibling(self, kinship_tree):
        """D's parent (B) has one sibling (C) — D's pibling."""
        result = set(SimpleNode.objects.piblings_of(kinship_tree["D"]))
        assert result == {kinship_tree["C"]}

    def test_piblings_of_top_level_child_is_empty(self, kinship_tree):
        """B's parent (A) is root and has no siblings — no piblings."""
        assert not SimpleNode.objects.piblings_of(kinship_tree["B"]).exists()

    def test_piblings_of_root_is_empty(self, kinship_tree):
        """Root node has no parent, hence no piblings."""
        assert not SimpleNode.objects.piblings_of(kinship_tree["A"]).exists()

    def test_instance_piblings_delegates(self, kinship_tree):
        """node.piblings() returns same QuerySet as piblings_of(node)."""
        qs_manager = set(SimpleNode.objects.piblings_of(kinship_tree["D"]))
        qs_instance = set(kinship_tree["D"].piblings())
        assert qs_manager == qs_instance


@pytest.mark.django_db
class TestNiblings:
    """niblings_of() and node.niblings()"""

    def test_niblings_of_node_with_nibling(self, kinship_tree):
        """B's sibling (C) has one child (F) — B's nibling."""
        result = set(SimpleNode.objects.niblings_of(kinship_tree["B"]))
        assert result == {kinship_tree["F"]}

    def test_niblings_of_node_with_multiple_niblings(self, kinship_tree):
        """C's sibling (B) has two children (D, E) — C's niblings."""
        result = set(SimpleNode.objects.niblings_of(kinship_tree["C"]))
        assert result == {kinship_tree["D"], kinship_tree["E"]}

    def test_niblings_of_only_child_is_empty(self, kinship_tree):
        """F is C's only child — F has no siblings, hence no niblings."""
        assert not SimpleNode.objects.niblings_of(kinship_tree["F"]).exists()

    def test_instance_niblings_delegates(self, kinship_tree):
        """node.niblings() returns same QuerySet as niblings_of(node)."""
        qs_manager = set(SimpleNode.objects.niblings_of(kinship_tree["B"]))
        qs_instance = set(kinship_tree["B"].niblings())
        assert qs_manager == qs_instance


@pytest.mark.django_db
class TestCousins:
    """cousins_of() and node.cousins() — symmetric degree (DD-016)"""

    def test_cousins_of_degree_2(self, kinship_tree):
        """D and F share common ancestor A, both at depth 3 — 1st cousins."""
        result = set(SimpleNode.objects.cousins_of(kinship_tree["D"], degree=2))
        assert result == {kinship_tree["F"]}

    def test_cousins_relation_holds_both_ways(self, kinship_tree):
        """E and F are also 1st cousins (E is D's sibling, same generation)."""
        result = set(SimpleNode.objects.cousins_of(kinship_tree["E"], degree=2))
        assert result == {kinship_tree["F"]}

    def test_cousins_of_asymmetric_cardinality(self, kinship_tree):
        """F's cousin set is {D, E} — larger than D's ({F}) or E's ({F}).

        The cousin relation is symmetric pairwise (D-F and F-D both hold,
        E-F and F-E both hold), but branches with unequal child counts
        produce unequal set *sizes* — this is correct, not a bug (DD-016).
        """
        result = set(SimpleNode.objects.cousins_of(kinship_tree["F"], degree=2))
        assert result == {kinship_tree["D"], kinship_tree["E"]}

    def test_cousins_of_degree_1_matches_siblings(self, kinship_tree):
        """degree=1 is degenerate: same set as siblings_of()."""
        cousins = set(SimpleNode.objects.cousins_of(kinship_tree["D"], degree=1))
        siblings = set(SimpleNode.objects.siblings_of(kinship_tree["D"]))
        assert cousins == siblings == {kinship_tree["E"]}

    def test_cousins_of_insufficient_ancestors_is_empty(self, kinship_tree):
        """Root has no ancestor 2 levels up — empty QuerySet, not an error."""
        assert not SimpleNode.objects.cousins_of(kinship_tree["A"], degree=2).exists()

    def test_cousins_of_does_not_cover_removed_case(self, kinship_tree):
        """G (depth 4) vs F (depth 3): documented "removed" limitation.

        Symmetric degree (Option B, DD-016) requires candidates at the
        *same* depth as node. G is one generation deeper than F, so no
        degree value pairs them — this is a known, documented gap, not
        a bug, deferred to post-v1.0.0 (genealogical `removed` parameter).
        """
        assert not SimpleNode.objects.cousins_of(kinship_tree["G"], degree=2).exists()
        assert not SimpleNode.objects.cousins_of(kinship_tree["G"], degree=3).exists()

    def test_cousins_of_invalid_degree_raises(self, kinship_tree):
        """degree < 1 is not a valid relationship — raises ValueError."""
        with pytest.raises(ValueError):
            SimpleNode.objects.cousins_of(kinship_tree["D"], degree=0)

    def test_cousins_of_default_degree_is_2(self, kinship_tree):
        """cousins_of(node) without degree defaults to degree=2."""
        default = set(SimpleNode.objects.cousins_of(kinship_tree["D"]))
        explicit = set(SimpleNode.objects.cousins_of(kinship_tree["D"], degree=2))
        assert default == explicit == {kinship_tree["F"]}

    def test_instance_cousins_delegates(self, kinship_tree):
        """node.cousins() returns same QuerySet as cousins_of(node)."""
        qs_manager = set(SimpleNode.objects.cousins_of(kinship_tree["D"], degree=2))
        qs_instance = set(kinship_tree["D"].cousins(degree=2))
        assert qs_manager == qs_instance

    def test_instance_cousins_default_degree(self, kinship_tree):
        """node.cousins() without arguments defaults to degree=2."""
        qs_manager = set(SimpleNode.objects.cousins_of(kinship_tree["D"]))
        qs_instance = set(kinship_tree["D"].cousins())
        assert qs_manager == qs_instance
