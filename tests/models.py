# =============================================================================
# tests/models.py — Concrete test models
#
# These models exist solely to exercise CladeNode in the test suite.
# They are not part of the clade public API.
#
# SimpleNode  — uses the default CASCADE deletion strategy
# AdoptNode   — uses the ADOPT deletion strategy (#43, activated later)
#
# Refs: DD-012, DD-014
#   https://gitlab.com/open-works/clade/-/issues/39  (DD-012)
#   https://gitlab.com/open-works/clade/-/issues/41  (DD-014)
#   https://gitlab.com/open-works/clade/-/issues/47  (this file)
# =============================================================================

from django.db import models

from clade.models import CladeNode


class SimpleNode(CladeNode):
    """Minimal concrete CladeNode for standard hierarchy tests.

    Uses the default CASCADE deletion strategy inherited from CladeNode.
    """

    name = models.CharField(max_length=64)

    class Meta(CladeNode.Meta):
        app_label = "tests"

    def __str__(self) -> str:
        return self.name


# AdoptNode is declared after ADOPT is implemented (#43).
# It will override the parent FK with on_delete=ADOPT.
#
# class AdoptNode(CladeNode):
#     from clade.deletion import ADOPT
#     name = models.CharField(max_length=64)
#     parent = models.ForeignKey(
#         "self",
#         null=True,
#         blank=True,
#         on_delete=ADOPT,
#         related_name="children",
#     )
#     class Meta(CladeNode.Meta):
#         app_label = "tests"
