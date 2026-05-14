# =============================================================================
# tests/models.py — Concrete test models.
#
# SimpleNode   Default CASCADE deletion (CladeNode default).
# AdoptNode    Custom ADOPT deletion — re-parents children on delete.
#
# Refs: DD-012 (#39), DD-014 (#41), #47, #49
# =============================================================================

from django.db import models

from clade.deletion import ADOPT
from clade.models import CladeNode


class SimpleNode(CladeNode):
    """Minimal concrete CladeNode for standard hierarchy tests."""

    name = models.CharField(max_length=64)

    class Meta(CladeNode.Meta):
        app_label = "tests"

    def __str__(self) -> str:
        return self.name


class AdoptNode(CladeNode):
    """Concrete CladeNode using ADOPT deletion strategy.

    When an AdoptNode is deleted, its direct children are re-parented
    to the grandparent rather than cascaded.
    """

    name = models.CharField(max_length=64)
    parent = models.ForeignKey(  # type: ignore[assignment]
        "self",
        null=True,
        blank=True,
        on_delete=ADOPT,
        related_name="children",
    )

    class Meta(CladeNode.Meta):
        app_label = "tests"

    def __str__(self) -> str:
        return self.name
