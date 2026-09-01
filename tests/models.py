# =============================================================================
# tests/models.py — Concrete test models.
#
# SimpleNode   Default CASCADE deletion (CladeNode default).
# AdoptNode    Custom ADOPT deletion — re-parents children on delete.
# AffinityDepartment / AffinityProject
#              Minimal AffinityRule pair (DD-005) — "geo" channel on
#              region/cost_center, "management" channel on manager/lead.
#              Mirrors the DD-005 §Declaration example almost verbatim.
#
# Refs: DD-005 (#5), DD-012 (#39), DD-014 (#41), #47, #49
# =============================================================================

from django.db import models

from clade.affinity import AffinityRule
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


class AffinityProject(CladeNode):
    """Passive Affinity target — never itself declares affinity_rules.

    Exercises the target-side (reverse-index) half of DD-005's
    bidirectional registry: saving an AffinityProject must trigger
    recalculation even though this model names no rules of its own.
    """

    title = models.CharField(max_length=64)
    cost_center = models.CharField(max_length=64, null=True, blank=True)
    lead = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"

    def __str__(self) -> str:
        return self.title


class AffinityDepartment(CladeNode):
    """Affinity source — declares two rules toward AffinityProject.

    Mirrors the DD-005 §Declaration example: "geo" on region/cost_center,
    "management" on manager/lead — two simultaneous channels toward the
    same target model.

    "geo" carries ``shared=True`` (DD-018, v0.6.0): AffinityDepartment
    and AffinityDepartmentAlt both reuse "geo" toward AffinityProject —
    a genuine junction under ``clade.E003`` — and consent to being
    chained through it via the declared-rule graph closure. "management"
    has no such junction and stays ``shared=False`` (the default).
    """

    name = models.CharField(max_length=64)
    region = models.CharField(max_length=64, null=True, blank=True)
    manager = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"
        affinity_rules = [
            AffinityRule(
                "region",
                to="tests.AffinityProject",
                target_field="cost_center",
                channel="geo",
                shared=True,
            ),
            AffinityRule(
                "manager",
                to="tests.AffinityProject",
                target_field="lead",
                channel="management",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class AffinityDepartmentAlt(CladeNode):
    """A second Affinity source reusing the "geo" channel name.

    DD-005: channel uniqueness is enforced per declaring model, not
    globally — two different source models may reuse the same channel
    label toward the same (or a different) target. Exercises the
    content_type_a scoping in ``_sync_target_instance`` (a naive
    channel-only scope would let this rule's recreate silently wipe out
    AffinityDepartment's "geo" rows for the same AffinityProject).

    ``shared=True`` (DD-018, v0.6.0): mirrors AffinityDepartment's own
    consent on "geo" — symmetric, per ``clade.E003``. Both sides must
    consent for AffinityProject to act as a valid pivot for closure
    under this channel; this fixture pair is the reference case for
    that opt-in.
    """

    name = models.CharField(max_length=64)
    zone = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"
        affinity_rules = [
            AffinityRule(
                "zone",
                to="tests.AffinityProject",
                target_field="cost_center",
                channel="geo",
                shared=True,
            ),
        ]

    def __str__(self) -> str:
        return self.name
