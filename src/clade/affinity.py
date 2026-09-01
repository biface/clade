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

from typing import TYPE_CHECKING, cast

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet


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
    shared : bool, default False
        Opt-in consent, per rule, to let this model act as a pivot for
        declared-rule graph closure under this ``channel`` name (DD-018,
        v0.6.0). A model's participation in a channel is only unlocked
        for chaining once every ``AffinityRule`` touching it under that
        name carries ``shared=True`` -- one-sided consent still fails
        ``clade.E003``. Purely declarative here: this flag has no effect
        on rule resolution or signal wiring by itself, it is read by
        ``clade.E003`` and the closure engine (``_recompute_shared_closure()``,
        this module).
    """

    def __init__(
        self,
        local_field: str,
        *,
        to: str,
        target_field: str,
        channel: str,
        shared: bool = False,
    ) -> None:
        self.local_field = local_field
        self.to = to
        self.target_field = target_field
        self.channel = channel
        self.shared = shared

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
            f"target_field={self.target_field!r}, channel={self.channel!r}, "
            f"shared={self.shared!r})"
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

    ``is_derived`` distinguishes a direct pair (materialised by the
    v0.5.0 signal handlers below, DD-005) from a derived pair produced
    by the declared-rule graph closure (DD-018, v0.6.0). Both kinds
    share this single table — no separate model.

    Do not create or update instances directly — maintained exclusively by
    the signal handlers wired via ``register_affinity_signals()`` (direct
    rows) and ``_recompute_shared_closure()`` below (derived rows).
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

    # django-stubs types BooleanField's `default` param as
    # `type[NOT_PROVIDED]` only in this stub version, rejecting an actual
    # bool default — same class of stub limitation as models.py:137.
    is_derived = models.BooleanField(
        default=False,  # type: ignore[reportArgumentType]
        help_text=(
            "False for a direct pair materialised by the v0.5.0 signal "
            "handlers (DD-005). True for a pair produced by the "
            "declared-rule graph closure (DD-018, v0.6.0) — see "
            "_recompute_shared_closure() in this module."
        ),
    )

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
            f"channel={self.channel!r}, value={self.value!r}, "
            f"is_derived={self.is_derived!r})"
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


# =============================================================================
# Closure engine — derived-pair materialisation (DD-018, #88, v0.6.0).
#
# _recompute_shared_closure(channel, seed_instances=None)
#     The computation only — callable in isolation for testing (#92).
#     Does not itself decide *when* to run: invalidation wiring
#     (post_save/post_delete hooks calling this after the existing
#     DD-005 direct-row resync) is a separate concern (#93).
#
# Algorithm: a fixed-point self-join over already-materialised Affinity
# rows (direct and derived alike) sharing (channel, value) through a
# common side — repeatedly infer a new pair for every two edges meeting
# at a shared node, until a pass adds nothing (DD-018: "the same shape
# as Floyd-Warshall over a finite, bounded set"). Never re-walks
# AffinityRule or compares field names on the pivot — correctness with
# respect to DD-004's "same shared value" requirement falls out of row
# equality on (channel, value), by construction.
#
# Restricted to channels with at least one shared=True rule: clade.E003
# already guarantees that any real junction (a model with degree > 1
# under a channel) is either fully consented or rejected at declaration
# time, so a channel with no shared=True rule at all can never contain a
# junction and closure over it would always be a no-op — skipped
# entirely as a cheap, correct pre-filter (not a semantic shortcut).
#
# Two rows only ever join if they share the same `value` (DD-004:
# transitivity holds only on directly shared values) — each distinct
# value under `channel` is therefore an independent closure problem,
# processed separately.
# =============================================================================


def _channel_has_shared_pivot(channel: str) -> bool:
    """True if at least one ``AffinityRule`` on *channel* has ``shared=True``.

    Necessary and sufficient as a pre-filter (not merely necessary):
    ``clade.E003`` rejects any junction (a model with degree > 1 under a
    channel) unless *every* incident rule is ``shared=True`` — so if no
    rule on this channel is ``shared=True`` at all, no junction can
    possibly exist under it, and the self-join below would find nothing
    to infer.
    """
    for rules in _source_registry.values():
        for rule in rules:
            if rule.channel == channel and rule.shared:
                return True
    return False


def _row_endpoints(row: Affinity) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return the two ``(content_type_id, object_id)`` endpoints of *row*.

    Same ``_id`` shadow-attribute / ``cast(int, ...)`` rationale as
    ``_other_side`` above: django-stubs types the PK-typed attributes
    (``object_id_a``/``object_id_b``) as their field class rather than
    the plain ``int`` they hold at runtime.
    """
    ct_a_id = row.content_type_a_id  # type: ignore[reportAttributeAccessIssue]
    ct_b_id = row.content_type_b_id  # type: ignore[reportAttributeAccessIssue]
    return (
        (ct_a_id, cast(int, row.object_id_a)),
        (ct_b_id, cast(int, row.object_id_b)),
    )


def _close_edge_set(
    edges: set[frozenset[tuple[int, int]]],
) -> set[frozenset[tuple[int, int]]]:
    """Return the transitive closure of *edges* (undirected simple graph).

    Repeated "join through a common side": if ``u-v`` and ``u-w`` are
    both edges (``v != w``), ``v-w`` is inferred. Iterates to a fixed
    point — each connected component converges to a complete graph
    (DD-018: "a ring of shared=True edges simply closes into one
    clique"). No depth limit, bounded by component size only, per
    DD-018 §Invalidation.
    """
    closed = set(edges)
    adjacency: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for edge in closed:
        u, v = tuple(edge)
        adjacency.setdefault(u, set()).add(v)
        adjacency.setdefault(v, set()).add(u)

    changed = True
    while changed:
        changed = False
        newly_found: set[frozenset[tuple[int, int]]] = set()
        for node, neighbors in adjacency.items():
            neighbor_list = list(neighbors)
            for i, v in enumerate(neighbor_list):
                for w in neighbor_list[i + 1 :]:
                    if v == w:
                        continue
                    pair = frozenset((v, w))
                    if pair not in closed:
                        newly_found.add(pair)
        if newly_found:
            changed = True
            closed |= newly_found
            for pair in newly_found:
                u, v = tuple(pair)
                adjacency.setdefault(u, set()).add(v)
                adjacency.setdefault(v, set()).add(u)
    return closed


def _close_one_value(channel: str, value: str) -> int:
    """Close the (channel, value) group — one independent closure problem.

    Reads every existing row (direct + derived) for this exact
    ``(channel, value)`` pair, computes the transitive closure in
    memory, and inserts one ``Affinity(..., is_derived=True)`` row per
    pair the closure adds that wasn't already present. Idempotent: a
    group with no new implied pair creates nothing (#92 acceptance:
    rerunning on an already-closed set is a no-op).
    """
    rows = list(Affinity.objects.filter(channel=channel, value=value))
    existing: set[frozenset[tuple[int, int]]] = set()
    for row in rows:
        a, b = _row_endpoints(row)
        if a != b:  # defensive: self-loops are not expected to exist
            existing.add(frozenset((a, b)))

    closed = _close_edge_set(existing)
    new_pairs = closed - existing
    if not new_pairs:
        return 0

    to_create = []
    for pair in new_pairs:
        (ct_a_id, obj_a), (ct_b_id, obj_b) = sorted(pair)
        to_create.append(
            Affinity(
                content_type_a=ContentType.objects.get_for_id(ct_a_id),
                object_id_a=obj_a,
                content_type_b=ContentType.objects.get_for_id(ct_b_id),
                object_id_b=obj_b,
                channel=channel,
                value=value,
                is_derived=True,
            )
        )
    Affinity.objects.bulk_create(to_create)
    return len(to_create)


def _values_for_instances(instances, channel: str) -> set[str]:
    """Distinct ``value``s that *instances* currently participate in
    under *channel* (direct or derived rows, either side)."""
    values: set[str] = set()
    for instance in instances:
        ct = ContentType.objects.get_for_model(type(instance))
        rows = Affinity.objects.filter(
            Q(content_type_a=ct, object_id_a=instance.pk)
            | Q(content_type_b=ct, object_id_b=instance.pk),
            channel=channel,
        ).values_list("value", flat=True)
        values.update(rows)
    return values


def _recompute_shared_closure(channel: str, seed_instances=None) -> int:
    """Recompute the derived-pair closure for *channel* (DD-018, #92).

    Restricted to channels with at least one ``shared=True`` rule (see
    ``_channel_has_shared_pivot``) — a channel with no such consent is
    left exactly as DD-005 already handles it: no derived rows, ever.

    ``seed_instances`` — a single node or an iterable of nodes — scopes
    the recomputation to the ``(channel, value)`` group(s) those
    instances currently participate in, rather than every value ever
    seen under *channel* (DD-018 §Invalidation: cost scales with
    component size, not with the whole channel). Omit it (``None``,
    the default) to recompute every value under *channel* in one call —
    the mode used here for direct, isolated testing; #93 wires the
    scoped mode into the post_save/post_delete invalidation path.

    Returns the number of new derived rows created (0 if the channel
    isn't shared, no seed value groups were found, or the closure was
    already complete).
    """
    if not _channel_has_shared_pivot(channel):
        return 0

    if seed_instances is not None:
        if hasattr(seed_instances, "_meta"):
            seed_instances = [seed_instances]
        values = _values_for_instances(seed_instances, channel)
        if not values:
            return 0
    else:
        values = set(
            Affinity.objects.filter(channel=channel).values_list("value", flat=True)
        )

    return sum(_close_one_value(channel, value) for value in values)


# =============================================================================
# Read side — affinities_of() / affinities_of_grouped() (#70).
#
# Affinity is inter-model by design (DD-005), so "the partner nodes" of a
# given node cannot in general be a single homogeneous QuerySet: a target
# model may be named by more than one source model under the same channel
# (channel uniqueness is per declaring model, not global — see
# TestAffinityChannelCollision in tests/test_affinity.py). Two entry
# points, not one flag-controlled function, so the return type never
# depends on the data found at runtime:
#
#   affinities_of(node, channel=None)          -> QuerySet[Model]
#       Single-model QuerySet. Raises HeterogeneousAffinityError if the
#       result would span more than one partner model.
#
#   affinities_of_grouped(node, channel=None)  -> dict[type[Model], QuerySet]
#       Never raises. One key per distinct partner model found.
#
# CladeNode.affinities()/affinities_grouped() and
# NodeManager.affinities_of()/affinities_of_grouped() are thin proxies
# onto these two functions (see clade/models.py, clade/managers.py).
# =============================================================================


class HeterogeneousAffinityError(Exception):
    """Raised by ``affinities_of()`` when partners span more than one model.

    Use ``affinities_of_grouped()`` instead when that is expected — e.g.
    two different source models reusing the same channel name toward the
    same target instance (DD-005: channel uniqueness is per declaring
    model, not global).
    """


def _affinity_rows_for(node: Model, channel: str | None = None) -> QuerySet[Affinity]:
    """Return the ``Affinity`` rows referencing *node*, on either side.

    Internal — callers use ``affinities_of()``/``affinities_of_grouped()``.
    """
    ct_self = ContentType.objects.get_for_model(type(node))
    qs = Affinity.objects.filter(
        Q(content_type_a=ct_self, object_id_a=node.pk)
        | Q(content_type_b=ct_self, object_id_b=node.pk)
    )
    if channel is not None:
        qs = qs.filter(channel=channel)
    return qs


def _default_manager(model: type[Model]):
    """Return *model*'s default manager — centralises the single
    ``# type: ignore`` needed since ``_default_manager`` is injected by
    Django's metaclass and invisible to a generic ``type[Model]``."""
    return model._default_manager  # type: ignore[reportAttributeAccessIssue]


def _model_label(model: type[Model]) -> str:
    """Return *model*'s ``app_label.ModelName`` label — same rationale
    as ``_default_manager`` above for the single ``# type: ignore``."""
    meta = model._meta  # type: ignore[reportAttributeAccessIssue]
    return meta.label


def _other_side(row: Affinity, ct_self: ContentType, self_pk) -> tuple[int, int]:
    """Return ``(content_type_id, object_id)`` for the side of *row*
    that is *not* ``(ct_self, self_pk)``. Same ``_id`` shadow-attribute
    rationale as the ``content_type_a_id`` comment further up this file.
    """
    ct_a_id = row.content_type_a_id  # type: ignore[reportAttributeAccessIssue]
    ct_b_id = row.content_type_b_id  # type: ignore[reportAttributeAccessIssue]
    if ct_a_id == ct_self.pk and row.object_id_a == self_pk:
        return ct_b_id, cast(int, row.object_id_b)
    return ct_a_id, cast(int, row.object_id_a)


def _rule_target_model_for_channel(node: Model, channel: str) -> type[Model] | None:
    """Resolve the declared target model for *node*'s own rule on
    *channel*, if *node*'s model declares one. Used only as a fallback
    to type an otherwise-empty result — see ``affinities_of()``.
    """
    meta = type(node)._meta  # type: ignore[reportAttributeAccessIssue]
    rules = getattr(meta, "affinity_rules", None)
    if not rules:
        return None
    for rule in rules:
        if rule.channel == channel:
            return rule.get_target_model()
    return None


def affinities_of_grouped(
    node: Model, channel: str | None = None
) -> dict[type[Model], QuerySet[Model]]:
    """Return ``{partner_model: QuerySet}`` for every partner of *node*.

    Never raises — the dict has one key per distinct model found on the
    "other side" of a matching ``Affinity`` row. In the common case
    (single declaring source, or a ``channel`` narrowing to one rule),
    the dict has exactly one key. Empty dict if *node* has no Affinity
    rows (optionally, for *channel*).
    """
    ct_self = ContentType.objects.get_for_model(type(node))
    rows = _affinity_rows_for(node, channel=channel)

    partner_ids: dict[int, set[int]] = {}
    for row in rows:
        other_ct_id, other_id = _other_side(row, ct_self, node.pk)
        partner_ids.setdefault(other_ct_id, set()).add(other_id)

    result: dict[type[Model], QuerySet[Model]] = {}
    for ct_id, ids in partner_ids.items():
        partner_model = ContentType.objects.get_for_id(ct_id).model_class()
        if partner_model is None:
            continue  # Stale ContentType (model removed) — skip defensively.
        result[partner_model] = _default_manager(partner_model).filter(pk__in=ids)
    return result


def affinities_of(node: Model, channel: str | None = None) -> QuerySet[Model]:
    """Return a single ``QuerySet`` of *node*'s Affinity partners.

    Raises ``HeterogeneousAffinityError`` if the matching rows reference
    more than one distinct partner model — use
    ``affinities_of_grouped()`` in that case instead.

    When no matching row exists, the result is an empty QuerySet. Its
    model is inferred from *node*'s own declared rule for *channel* when
    possible (giving a correctly-typed empty QuerySet); if that cannot
    be determined (no ``channel``, or *node* declares no matching rule —
    e.g. *node* is a passive target with no Affinity rows yet), an empty
    ``Affinity`` QuerySet is returned as a documented fallback. This is
    behaviourally indistinguishable from any other empty QuerySet for
    iteration, ``.exists()``, ``.count()``, etc. — only ``.model``
    reports ``Affinity`` rather than the (undeterminable) partner type.
    """
    grouped = affinities_of_grouped(node, channel=channel)

    if len(grouped) > 1:
        labels = ", ".join(_model_label(m) for m in grouped)
        where = f" on channel {channel!r}" if channel else ""
        raise HeterogeneousAffinityError(
            f"affinities_of({node!r}{where}) spans more than one partner "
            f"model ({labels}) — use affinities_of_grouped() instead."
        )

    if grouped:
        return next(iter(grouped.values()))

    if channel is not None:
        target_model = _rule_target_model_for_channel(node, channel)
        if target_model is not None:
            return _default_manager(target_model).none()

    return Affinity.objects.none()  # type: ignore[return-value]
