# =============================================================================
# clade/apps.py — Django application configuration.
#
# Module-level: registers "affinity_rules" as a recognised Meta option
# (see _register_affinity_rules_meta_option below) — must run before any
# models.py is imported, hence at module load time, not inside ready().
#
# CladeConfig.ready() wires two independent signal sets:
#
#   1. Path maintenance (clade/signals.py) — on all concrete CladeNode
#      subclasses. Uses two mechanisms:
#        - class_prepared   Catches subclasses defined *after* ready() runs
#                            (dynamic models, test factories, etc.).
#        - iter_concrete_subclasses
#                            Connects to subclasses already loaded at
#                            startup.
#
#   2. Affinity maintenance (clade/affinity.py) — delegated entirely to
#      clade.affinity.register_affinity_signals(), which owns its own
#      registry-building and signal-wiring logic (DD-005 §Maintenance).
#
# dispatch_uid prevents duplicate connections if the app is reloaded.
#
# Refs: DD-005 (#5), DD-009 (#9), DD-013 (#40), #44
# =============================================================================

from django.apps import AppConfig


def _register_affinity_rules_meta_option() -> None:
    """Register ``affinity_rules`` as a recognised ``Meta`` option.

    Django validates ``class Meta`` contents against a closed list
    (the module-level ``django.db.models.options.DEFAULT_NAMES`` tuple)
    and raises ``TypeError`` for any unrecognised attribute.
    ``affinity_rules`` is not a built-in Django Meta option, so without
    this patch, any user model declaring it (per DD-005's documented
    syntax, "à la Meta.constraints") would fail at class-definition time.

    Safe to run exactly once, at module import time (not inside
    ``ready()``): Django imports every installed app's ``apps.py`` (to
    discover its ``AppConfig``) *before* importing any app's
    ``models.py`` — this patch is therefore guaranteed to be in place
    before any model using ``Meta.affinity_rules`` is defined, regardless
    of ``clade``'s position in ``INSTALLED_APPS``.

    This relies on an undocumented Django internal (the module-level
    ``DEFAULT_NAMES`` tuple, not a public API) — a known point of
    fragility to re-verify on Django version upgrades (see DD-009
    progressive support matrix).
    """
    from django.db.models import options

    if "affinity_rules" not in options.DEFAULT_NAMES:
        options.DEFAULT_NAMES = options.DEFAULT_NAMES + ("affinity_rules",)


_register_affinity_rules_meta_option()


class CladeConfig(AppConfig):
    name = "clade"
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    # django-stubs types default_auto_field as cached_property — known limitation.

    def ready(self) -> None:
        from django.core.checks import register as register_check
        from django.db.models.signals import class_prepared, post_delete, post_save

        from clade._discovery import iter_concrete_subclasses
        from clade.affinity import register_affinity_signals
        from clade.checks import (
            check_affinity_channel_uniqueness,
            check_affinity_field_types,
        )
        from clade.models import CladeNode
        from clade.signals import on_cladenode_delete, on_cladenode_save

        def connect(model) -> None:
            """Register path-maintenance signals for one concrete model."""
            uid = model._meta.label  # e.g. "myapp.Department"
            post_save.connect(
                on_cladenode_save,
                sender=model,
                dispatch_uid=f"clade.signals.save.{uid}",
                weak=False,
            )
            post_delete.connect(
                on_cladenode_delete,
                sender=model,
                dispatch_uid=f"clade.signals.delete.{uid}",
                weak=False,
            )

        def on_class_prepared(sender, **kwargs) -> None:
            """Connect signals when a new CladeNode subclass is declared."""
            if (
                sender is not CladeNode
                and hasattr(sender, "_meta")
                and not sender._meta.abstract
                and issubclass(sender, CladeNode)
            ):
                connect(sender)

        # 1. Future subclasses (dynamic models, test factories).
        class_prepared.connect(
            on_class_prepared,
            dispatch_uid="clade.class_prepared",
        )

        # 2. Concrete subclasses already loaded at startup.
        for model in iter_concrete_subclasses(CladeNode):
            connect(model)

        # 3. Affinity maintenance — independent registry/signal set (DD-005).
        register_affinity_signals()

        # 4. Affinity checks — clade.E001 (channel uniqueness), clade.E002
        #    (field-type allowlist). Run at `manage.py check` / CI startup.
        # Each check function returns Error(..., id="clade.EXXX") objects —
        # register() itself takes no id kwarg, only optional tags.
        register_check(check_affinity_channel_uniqueness)
        register_check(check_affinity_field_types)
