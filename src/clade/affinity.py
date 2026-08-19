# =============================================================================
# clade/affinity.py — Affinity: non-hierarchical shared-attribute grouping.
#
# AffinityRule            Declarative rule, registered via Meta.affinity_rules
#                         (à la Meta.constraints). Resolved lazily via
#                         apps.get_model() — no hard import coupling between
#                         user apps.
#
# Affinity                Concrete, single global table (django.contrib.
#                         contenttypes-backed). Stores materialised pairwise
#                         relationships — never computed on-the-fly (DD-005).
#
# register_affinity_signals()
#                         Builds the bidirectional AffinityRule registry and
#                         wires post_save/post_delete on the union of source
#                         and target models. Called once from
#                         CladeConfig.ready() (clade/apps.py) — mirrors the
#                         logic/wiring split already used for path
#                         maintenance (clade/signals.py + clade/apps.py).
#
# Scope
# -----
# Only concrete CladeNode subclasses are scanned for Meta.affinity_rules —
# consistent with DD-005 ("Any two CladeNode subclasses can enter an
# Affinity relationship"). A model declaring affinity_rules without being a
# CladeNode subclass is not supported in v0.5.0.
#
# Field-type allowlist
# ---------------------
# local_field/target_field are restricted to an explicit allowlist of
# scalar field types (see _ALLOWED_FIELD_TYPES below), enforced by
# clade.E002 (clade/checks.py) — not repeated here.
#
# Refs: DD-004 (#4), DD-005 (#5, amended 2026-08 — allowlist)
# =============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

if TYPE_CHECKING:
    from django.db.models import Model


class AffinityRule:
    """Declarative Affinity rule, registered via ``Meta.affinity_rules``.

    Follows the same declarative pattern as ``Meta.constraints``::

        class Department(CladeNode):
            region = models.CharField(...)

            class Meta(CladeNode.Meta):
                affinity_rules = [
                    AffinityRule(
                        "region", to="projects.Project",
                        target_field="cost_center", channel="geo",
                    ),
                ]

    Parameters
    ----------
    local_field : str
        Name of the scalar field on the declaring model.
    to : str
        Target model, using the ``"app_label.Model"`` string convention
        (identical to ``ForeignKey(to=...)``). Resolved lazily via
        ``apps.get_model()`` — never at declaration time, so no hard
        import coupling between user apps.
    target_field : str
        Explicit field name on the target model. Never inferred by
        same-name matching (DD-005: two unrelated models sharing a
        field name, e.g. ``name``, must not silently enter Affinity).
    channel : str
        Free-form label identifying the rule and, transitively, its
        target model. Must be unique within a single model's
        ``affinity_rules`` list (enforced by ``clade.E001``) — reusable
        across different source models.
    """

    def __init__(
        self, local_field: str, *, to: str, target_field: str, channel: str
    ) -> None:
        self.local_field = local_field
        self.to = to
        self.target_field = target_field
        self.channel = channel

    def get_target_model(self) -> type[Model]:
        """Resolve ``to`` to a concrete model class via ``apps.get_model()``.

        Lazy by design — called only when a rule is actually evaluated
        (registry construction, checks, signal handling), never at
        declaration time.
        """
        from django.apps import apps

        return apps.get_model(self.to)

    def __repr__(self) -> str:  # pragma: no cover — debugging aid only
        return (
            f"AffinityRule({self.local_field!r}, to={self.to!r}, "
            f"target_field={self.target_field!r}, channel={self.channel!r})"
        )


# =============================================================================
# Affinity — concrete, single global table.
#
# Two GenericForeignKey sides (content_type_a/object_id_a,
# content_type_b/object_id_b) rather than one join table per model pair
# (DD-005 §Storage): any two CladeNode subclasses can enter an Affinity
# relationship without clade generating per-pair schema.
#
# One row per pair, not two mirrored rows — see indexing note below.
# =============================================================================


class Affinity(models.Model):
    """A single materialised Affinity relationship between two nodes.

    One row per pair (not two mirrored rows): ``node.affinities()`` reads
    across both sides, so consistency has exactly one row to maintain per
    relationship rather than two that could drift apart.

    Do not create or update instances directly — maintained exclusively by
    the signal handlers wired via ``register_affinity_signals()``.
    """

    objects = models.Manager()

    content_type_a = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    object_id_a = models.PositiveBigIntegerField()
    side_a = GenericForeignKey("content_type_a", "object_id_a")

    content_type_b = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    object_id_b = models.PositiveBigIntegerField()
    side_b = GenericForeignKey("content_type_b", "object_id_b")

    channel = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    class Meta:
        indexes = [
            # Duplicated composite index on both sides: post_save/post_delete
            # must look up existing rows regardless of which side the saved
            # instance occupies (a model may be a source in one rule and a
            # passive target in another — see DD-005 §Maintenance).
            models.Index(
                fields=["content_type_a", "object_id_a", "channel", "value"],
                name="clade_affin_side_a_idx",
            ),
            models.Index(
                fields=["content_type_b", "object_id_b", "channel", "value"],
                name="clade_affin_side_b_idx",
            ),
        ]

    def __repr__(self) -> str:  # pragma: no cover — debugging aid only
        ct_a_id = self.content_type_a_id  # type: ignore[reportAttributeAccessIssue]
        ct_b_id = self.content_type_b_id  # type: ignore[reportAttributeAccessIssue]
        return (
            f"Affinity(a=({ct_a_id}, {self.object_id_a}), "
            f"b=({ct_b_id}, {self.object_id_b}), "
            f"channel={self.channel!r}, value={self.value!r})"
        )


# =============================================================================
# Registry — built once by register_affinity_signals(), called from
# CladeConfig.ready(). See clade/apps.py for the call site.
#
# _source_registry   model → its declared AffinityRule list.
# _target_registry   model → [(source_model, AffinityRule), ...] naming it
#                     as a passive target.
#
# Both registries are needed so that saving *either* side of a pair
# triggers recalculation — the gap DD-005 closed (a passive target model,
# never itself declaring affinity_rules, would otherwise leave stale
# Affinity rows when its own matched field changes).
# =============================================================================

_source_registry: dict[type[Model], list[AffinityRule]] = {}
_target_registry: dict[type[Model], list[tuple[type[Model], AffinityRule]]] = {}


def _build_registry() -> tuple[
    dict[type[Model], list[AffinityRule]],
    dict[type[Model], list[tuple[type[Model], AffinityRule]]],
]:
    """Scan concrete CladeNode subclasses for ``Meta.affinity_rules``.

    Only ``CladeNode`` subclasses are scanned (DD-005 §Storage: "Any two
    CladeNode subclasses can enter an Affinity relationship") — a plain
    Django model declaring ``affinity_rules`` without being a CladeNode
    subclass is not supported in v0.5.0.
    """
    from clade._discovery import iter_concrete_subclasses
    from clade.models import CladeNode

    source_registry: dict[type[Model], list[AffinityRule]] = {}
    target_registry: dict[type[Model], list[tuple[type[Model], AffinityRule]]] = {}

    for model in iter_concrete_subclasses(CladeNode):
        meta = model._meta  # type: ignore[reportAttributeAccessIssue]
        rules = getattr(meta, "affinity_rules", None)
        if not rules:
            continue
        source_registry[model] = list(rules)
        for rule in rules:
            target_model = rule.get_target_model()
            target_registry.setdefault(target_model, []).append((model, rule))

    return source_registry, target_registry


def register_affinity_signals() -> None:
    """Build the Affinity registry and wire post_save/post_delete.

    Called once from ``CladeConfig.ready()``. Connects on the union of
    every model that declares ``affinity_rules`` (source) and every model
    named as a target by at least one rule (passive target) — the
    bidirectional coverage required by DD-005 §Maintenance.

    Safe to call more than once (e.g. app reload in tests): signal
    connections use ``dispatch_uid`` and Django's ``Signal.connect()`` is
    itself idempotent per ``(receiver, sender, dispatch_uid)``.
    """
    from django.db.models.signals import post_delete, post_save

    global _source_registry, _target_registry
    _source_registry, _target_registry = _build_registry()

    connected_models = set(_source_registry) | set(_target_registry)

    for model in connected_models:
        meta = model._meta  # type: ignore[reportAttributeAccessIssue]
        uid = meta.label  # e.g. "myapp.Department"
        post_save.connect(
            on_affinity_save,
            sender=model,
            dispatch_uid=f"clade.affinity.save.{uid}",
            weak=False,
        )
        post_delete.connect(
            on_affinity_delete,
            sender=model,
            dispatch_uid=f"clade.affinity.delete.{uid}",
            weak=False,
        )


# =============================================================================
# Signal handlers.
#
# Both handlers use a full delete-then-recreate strategy for the affected
# (instance, channel) scope, rather than diffing old/new matches. This is
# a deliberate simplification: Django's post_save does not carry the
# previous field value, and diffing would require an extra read (or a
# pre_save snapshot) for a benefit that only matters at very large scale.
# Given the "non-scanning" guarantee in DD-005 concerns the *read* index,
# not the write path — a write-time scan is an accepted, documented cost
# (see DD-005 §Constraints) — full recreate keeps the logic trivially
# correct, at the cost of extra churn on unchanged matches. Revisit at
# v0.8.0 (Performance & scale) if this proves too costly in practice.
#
# NULL handling: a value of None never matches anything (skip early,
# regardless of side) — Django's `filter(field=None)` translates to
# `IS NULL` and would otherwise silently match other NULLs. This mirrors
# ordinary SQL equality semantics rather than treating NULL as a wildcard.
# =============================================================================


def _sync_source_instance(
    instance, source_model: type[Model], rule: AffinityRule
) -> None:
    """(Re)synchronise Affinity rows for one *(source instance, rule)* pair.

    Deletes every previously materialised row for this instance under
    this rule's channel, then recreates one row per current match on the
    target model. A no-op recreate (value unchanged, same matches) still
    costs a delete + re-insert — see module-level note above.
    """
    ct_source = ContentType.objects.get_for_model(source_model)

    Affinity.objects.filter(
        content_type_a=ct_source,
        object_id_a=instance.pk,
        channel=rule.channel,
    ).delete()

    value = getattr(instance, rule.local_field, None)
    if value is None:
        return  # NULL never matches — nothing to recreate.

    target_model = rule.get_target_model()
    ct_target = ContentType.objects.get_for_model(target_model)
    matches = target_model._default_manager.filter(**{rule.target_field: value})

    Affinity.objects.bulk_create(
        [
            Affinity(
                content_type_a=ct_source,
                object_id_a=instance.pk,
                content_type_b=ct_target,
                object_id_b=match.pk,
                channel=rule.channel,
                value=str(value),
            )
            for match in matches
            if not (ct_target.pk == ct_source.pk and match.pk == instance.pk)
        ]
    )


def _sync_target_instance(
    instance,
    target_model: type[Model],
    source_model: type[Model],
    rule: AffinityRule,
) -> None:
    """(Re)synchronise Affinity rows for one *(target instance, rule)* pair.

    Mirrors ``_sync_source_instance`` for the passive-target side. Scoped
    by ``content_type_a=ct_source`` in addition to channel: two different
    source models may reuse the same channel name against the same
    target model (DD-005 — channel uniqueness is per-source-model, not
    global), so scoping only by channel would let one rule's recreate
    silently wipe out another's rows.
    """
    ct_target = ContentType.objects.get_for_model(target_model)
    ct_source = ContentType.objects.get_for_model(source_model)

    Affinity.objects.filter(
        content_type_a=ct_source,
        content_type_b=ct_target,
        object_id_b=instance.pk,
        channel=rule.channel,
    ).delete()

    value = getattr(instance, rule.target_field, None)
    if value is None:
        return  # NULL never matches — nothing to recreate.

    sources = source_model._default_manager.filter(**{rule.local_field: value})

    Affinity.objects.bulk_create(
        [
            Affinity(
                content_type_a=ct_source,
                object_id_a=src.pk,
                content_type_b=ct_target,
                object_id_b=instance.pk,
                channel=rule.channel,
                value=str(value),
            )
            for src in sources
            if not (ct_source.pk == ct_target.pk and src.pk == instance.pk)
        ]
    )


def on_affinity_save(sender, instance, **kwargs) -> None:
    """post_save: resynchronise Affinity rows for the saved instance.

    Handles both roles independently — a model may declare rules
    (source) *and* be named as a target by another rule at the same
    time; both branches run when applicable.
    """
    for rule in _source_registry.get(sender, []):
        _sync_source_instance(instance, sender, rule)
    for source_model, rule in _target_registry.get(sender, []):
        _sync_target_instance(instance, sender, source_model, rule)


def on_affinity_delete(sender, instance, **kwargs) -> None:
    """post_delete: purge every Affinity row referencing the deleted
    instance, on either side, regardless of channel.

    Unconditional — does not consult the registry, since a deleted
    instance's rows must be purged even if it no longer resolves to a
    live rule (e.g. mid-refactor, or a target-only model).
    """
    ct = ContentType.objects.get_for_model(sender)
    Affinity.objects.filter(
        Q(content_type_a=ct, object_id_a=instance.pk)
        | Q(content_type_b=ct, object_id_b=instance.pk)
    ).delete()
