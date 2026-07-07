# =============================================================================
# tests/conftest.py — Shared fixtures for the clade test suite
#
# Refs: DD-006, DD-012, DD-013
#   https://gitlab.com/open-works/clade/-/issues/47
# =============================================================================

import pytest


@pytest.fixture
def tree(db):
    """Reference tree for hierarchy tests.

    Structure::

        A (root)
        ├── B
        │   ├── D
        │   │   └── G
        │   └── E
        └── C

    Path values (e.g. A.path="1", B.path="1.2") are populated
    automatically by the post_save signal once #44 is implemented.

    Returns a dict keyed by node name for convenient access::

        def test_something(tree):
            assert tree["B"].parent == tree["A"]
    """
    from tests.models import SimpleNode

    a = SimpleNode.objects.create(name="A")
    b = SimpleNode.objects.create(name="B", parent=a)
    c = SimpleNode.objects.create(name="C", parent=a)
    d = SimpleNode.objects.create(name="D", parent=b)
    e = SimpleNode.objects.create(name="E", parent=b)
    g = SimpleNode.objects.create(name="G", parent=d)

    # Refresh from DB so all fields (including path, once #44 is active)
    # reflect the persisted state rather than in-memory defaults.
    for node in (a, b, c, d, e, g):
        node.refresh_from_db()

    return {"A": a, "B": b, "C": c, "D": d, "E": e, "G": g}


@pytest.fixture
def kinship_tree(db):
    """Extended reference tree for pibling/nibling/cousin tests (DD-016, #56).

    A separate fixture from ``tree`` — deliberately not shared with it —
    because the extended-kinship tests need a node under ``C`` (``F``) to
    exercise a non-degenerate cousin relationship. Adding that node to the
    shared ``tree`` fixture would break existing assertions that depend on
    ``C`` being a leaf (e.g. ``TestIsRootIsLeaf.test_is_leaf_true_for_leaves``
    in ``test_hierarchy.py``).

    Structure::

        A (root)
        ├── B
        │   ├── D
        │   │   └── G
        │   └── E
        └── C
            └── F

    ``D`` and ``F`` (and ``E`` and ``F``) are 1st cousins (common ancestor
    ``A``, both at depth 3). ``G`` is one level deeper than ``F`` — it
    demonstrates the documented "removed" limitation of the symmetric
    degree definition (DD-016): ``cousins_of(G, degree=2)`` returns an
    empty QuerySet, since Option B does not cover different-depth cousins.

    Returns a dict keyed by node name for convenient access::

        def test_something(kinship_tree):
            assert kinship_tree["D"].parent == kinship_tree["B"]
    """
    from tests.models import SimpleNode

    a = SimpleNode.objects.create(name="A")
    b = SimpleNode.objects.create(name="B", parent=a)
    c = SimpleNode.objects.create(name="C", parent=a)
    d = SimpleNode.objects.create(name="D", parent=b)
    e = SimpleNode.objects.create(name="E", parent=b)
    f = SimpleNode.objects.create(name="F", parent=c)
    g = SimpleNode.objects.create(name="G", parent=d)

    for node in (a, b, c, d, e, f, g):
        node.refresh_from_db()

    return {"A": a, "B": b, "C": c, "D": d, "E": e, "F": f, "G": g}
