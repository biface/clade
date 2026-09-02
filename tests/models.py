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


class AffinityChainA(CladeNode):
    """Permanent 4-node ring fixture for DD-018 transitivity tests
    (#94, #95, #96): A -> B -> C -> D -> A, all ``shared=True`` under
    channel "chain".

    A genuine declared-rule ring — each node both declares (toward its
    successor) and is targeted (by its predecessor), giving every node
    degree 2 under "chain". This is ``clade.E003``'s baseline *valid*
    case for a fully-consented cycle, and the closure engine's
    reference case for "a ring of shared=True edges simply closes into
    one clique" (DD-018). Permanent (not ``isolate_apps``) because
    ``AffinityRule.get_target_model()`` resolves ``to=`` via the
    *global* Django app registry — a chain of 3+ mutually-referencing
    models declared inside a single ``isolate_apps`` block cannot
    resolve each other (each gets its own isolated registry instead of
    the global one), so multi-hop chain scenarios need real, permanent
    models. Single-edge extensions onto this permanent ring (e.g. a
    new non-consenting rule) still use ``isolate_apps`` normally, since
    they only need to resolve *toward* an already-permanent target —
    the same pattern already used by ``TestAffinityChecks`` for
    E001/E002.
    """

    v = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"
        affinity_rules = [
            AffinityRule(
                "v",
                to="tests.AffinityChainB",
                target_field="v",
                channel="chain",
                shared=True,
            ),
        ]

    def __str__(self) -> str:
        return f"ChainA({self.pk})"


class AffinityChainB(CladeNode):
    """Second node of the AffinityChainA ring — see its docstring."""

    v = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"
        affinity_rules = [
            AffinityRule(
                "v",
                to="tests.AffinityChainC",
                target_field="v",
                channel="chain",
                shared=True,
            ),
        ]

    def __str__(self) -> str:
        return f"ChainB({self.pk})"


class AffinityChainC(CladeNode):
    """Third node of the AffinityChainA ring — see its docstring."""

    v = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"
        affinity_rules = [
            AffinityRule(
                "v",
                to="tests.AffinityChainD",
                target_field="v",
                channel="chain",
                shared=True,
            ),
        ]

    def __str__(self) -> str:
        return f"ChainC({self.pk})"


class AffinityChainD(CladeNode):
    """Fourth node of the AffinityChainA ring, closing the cycle back to
    A — see AffinityChainA's docstring."""

    v = models.CharField(max_length=64, null=True, blank=True)

    class Meta(CladeNode.Meta):
        app_label = "tests"
        affinity_rules = [
            AffinityRule(
                "v",
                to="tests.AffinityChainA",
                target_field="v",
                channel="chain",
                shared=True,
            ),
        ]

    def __str__(self) -> str:
        return f"ChainD({self.pk})"
