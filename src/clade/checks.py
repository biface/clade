# =============================================================================
# clade/checks.py — django.core.checks registrations for Affinity.
#
# clade.E001   channel must be unique within a single model's
#              affinity_rules list (DD-005 §Declaration).
# clade.E002   local_field/target_field must be one of an explicit
#              allowlist of scalar field types (DD-005 §Constraints,
#              amended — see comment on #5).
#
# Both checks fail at `manage.py check` / CI startup — never silently at
# write time. Registered from CladeConfig.ready() via
# django.core.checks.register().
#
# Refs: DD-005 (#5, amendment: field-type allowlist)
# =============================================================================

from __future__ import annotations

from django.core.checks import Error

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
