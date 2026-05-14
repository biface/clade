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
