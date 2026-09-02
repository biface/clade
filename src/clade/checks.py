# =============================================================================
# clade/checks.py — django.core.checks registrations for Affinity.
#
# clade.E001   channel must be unique within a single model's
#              affinity_rules list (DD-005 §Declaration).
# clade.E002   local_field/target_field must be one of an explicit
#              allowlist of scalar field types (DD-005 §Constraints,
#              amended — see comment on #5).
# clade.E003   symmetric shared=True consent required to let a model
#              act as a pivot for declared-rule graph closure under a
#              given channel (DD-018 §Guard against accidental chaining).
#
# All three checks fail at `manage.py check` / CI startup — never
# silently at write time or from instance data. Registered from
# CladeConfig.ready() via django.core.checks.register().
#
# Refs: DD-005 (#5, amendment: field-type allowlist), DD-018 (#88)
# =============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.checks import Error

if TYPE_CHECKING:
    from clade.affinity import AffinityRule

# Allowlist, not a blacklist (DD-005 amendment): an unrecognised or future
# field type is rejected by default rather than silently accepted.
_ALLOWED_FIELD_TYPES: tuple[str, ...] = (
    "CharField",
    "TextField",
    "SlugField",
    "EmailField",
    "URLField",
    "GenericIPAddressField",
    "UUIDField",
    "IntegerField",
    "SmallIntegerField",
    "BigIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "PositiveBigIntegerField",
    "BooleanField",
    "DateField",
    "DateTimeField",
    "TimeField",
    "DurationField",
    "DecimalField",
)


def _iter_affinity_declaring_models():
    """Yield every concrete CladeNode subclass declaring affinity_rules."""
    from clade._discovery import iter_concrete_subclasses
    from clade.models import CladeNode

    for model in iter_concrete_subclasses(CladeNode):
        meta = model._meta  # type: ignore[reportAttributeAccessIssue]
        rules = getattr(meta, "affinity_rules", None)
        if rules:
            yield model, rules


def check_affinity_channel_uniqueness(app_configs, **kwargs):
    """clade.E001 — channel must be unique within one model's affinity_rules.

    Uniqueness is per declaring model, not global: two different source
    models may reuse the same channel name (DD-005).
    """
    errors = []
    for model, rules in _iter_affinity_declaring_models():
        seen: dict[str, int] = {}
        for rule in rules:
            seen[rule.channel] = seen.get(rule.channel, 0) + 1
        duplicates = [channel for channel, count in seen.items() if count > 1]
        model_label = model._meta.label  # type: ignore[reportAttributeAccessIssue]
        for channel in duplicates:
            errors.append(
                Error(
                    f"Duplicate Affinity channel {channel!r} in "
                    f"{model_label}.Meta.affinity_rules.",
                    hint=(
                        "Each channel must be unique within a single "
                        "model's affinity_rules list, even across "
                        "different target models."
                    ),
                    obj=model,
                    id="clade.E001",
                )
            )
    return errors


def check_affinity_field_types(app_configs, **kwargs):
    """clade.E002 — local_field/target_field must be on the scalar allowlist.

    Checks both sides of every rule: the declaring model's local_field,
    and the resolved target model's target_field. Both are validated
    independently — an allowed local_field paired with a disallowed
    target_field (or vice versa) is still an error.
    """
    errors = []
    for model, rules in _iter_affinity_declaring_models():
        for rule in rules:
            errors.extend(_check_field(model, rule.local_field, rule, model))
            try:
                target_model = rule.get_target_model()
            except LookupError:
                # Unresolvable `to` is out of scope for E002 — a separate,
                # not-yet-implemented check would cover that case.
                continue
            errors.extend(_check_field(model, rule.target_field, rule, target_model))
    return errors


def _check_field(declaring_model, field_name, rule, field_owner_model) -> list[Error]:
    try:
        field = field_owner_model._meta.get_field(field_name)
    except Exception:
        # Unresolvable field name is out of scope for E002 — a missing/
        # misspelled field is a distinct error class, not a type error.
        return []

    field_type = type(field).__name__
    if field_type in _ALLOWED_FIELD_TYPES:
        return []

    return [
        Error(
            f"AffinityRule channel {rule.channel!r} on "
            f"{declaring_model._meta.label} references "
            f"{field_owner_model._meta.label}.{field_name}, a "
            f"{field_type} — not an allowed Affinity field type.",
            hint=(
                "local_field/target_field must be one of: "
                + ", ".join(_ALLOWED_FIELD_TYPES)
                + ". ManyToManyField, FileField/ImageField, BinaryField, "
                "JSONField, FloatField and ForeignKey/OneToOneField are "
                "explicitly excluded (see amendment on issue #5)."
            ),
            obj=declaring_model,
            id="clade.E002",
        )
    ]


def _iter_affinity_edges():
    """Yield ``(source_model, target_model, rule)`` for every resolvable rule.

    One edge per declared ``AffinityRule`` whose ``to`` resolves to a real
    model. Unresolvable ``to`` (``LookupError``) is skipped, same as
    ``clade.E002`` — a separate, not-yet-implemented check would cover a
    dangling reference.
    """
    for model, rules in _iter_affinity_declaring_models():
        for rule in rules:
            try:
                target_model = rule.get_target_model()
            except LookupError:
                continue
            yield model, target_model, rule


def check_affinity_shared_channel_consent(app_configs, **kwargs):
    """clade.E003 — symmetric ``shared=True`` consent for channel reuse.

    Following declared-rule chains at closure time (DD-018) introduces a
    naming-collision risk: two ``AffinityRule``s declared independently
    can reuse the same ``channel`` name for unrelated purposes and, if
    they share a common model as an endpoint, silently form a chain
    nobody intended.

    For a given ``channel`` name, build the graph of edges (declaring
    model <-> resolved target model) carrying that name. Any model with
    degree > 1 in that graph is a junction: the chain through it is
    rejected unless **every** incident ``AffinityRule`` carries
    ``shared=True`` — one-sided consent still fails. Two edges sharing a
    channel name with no common model are never flagged, ``shared`` or
    not: only a genuine junction triggers this check.

    Schema/declaration-time only — built entirely from
    ``Meta.affinity_rules`` across the app registry, never from instance
    data or ``value``.
    """
    edges_by_channel: dict[str, list[tuple[type, type, AffinityRule]]] = {}
    for source, target, rule in _iter_affinity_edges():
        edges_by_channel.setdefault(rule.channel, []).append((source, target, rule))

    errors: list[Error] = []
    for channel, edges in edges_by_channel.items():
        incident: dict[type, list[tuple[type, type, AffinityRule]]] = {}
        for edge in edges:
            source, target, _rule = edge
            incident.setdefault(source, []).append(edge)
            incident.setdefault(target, []).append(edge)

        for model, model_edges in incident.items():
            # Deduplicate: a rule targeting its own declaring model under
            # this channel is appended to `incident[model]` twice (once
            # as source, once as target) — dedupe by rule identity so a
            # single self-referencing edge is never mistaken for a
            # junction of degree 2.
            unique_edges = list(
                {
                    id(rule): (source, target, rule)
                    for source, target, rule in model_edges
                }.values()
            )
            if len(unique_edges) <= 1:
                continue

            non_consenting = [e for e in unique_edges if not e[2].shared]
            if not non_consenting:
                continue

            model_label = model._meta.label  # type: ignore[reportAttributeAccessIssue]
            edge_descriptions = ", ".join(
                f"{src._meta.label}->{tgt._meta.label} (shared={rule.shared!r})"
                for src, tgt, rule in unique_edges
            )
            errors.append(
                Error(
                    f"{model_label} is a junction for Affinity channel "
                    f"{channel!r} (edges: {edge_descriptions}) but not "
                    "every incident AffinityRule has shared=True.",
                    hint=(
                        "Declared-rule graph closure (DD-018) only "
                        f"chains through {model_label} under channel "
                        f"{channel!r} if every AffinityRule touching it "
                        "under that name sets shared=True — one-sided "
                        "consent is rejected."
                    ),
                    obj=model,
                    id="clade.E003",
                )
            )
    return errors
