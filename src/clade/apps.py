# =============================================================================
# clade/apps.py — Django application configuration.
#
# Connects path-maintenance signals to all concrete CladeNode subclasses
# in CladeConfig.ready().  Uses two mechanisms:
#
#   1. class_prepared   Catches subclasses defined *after* ready() runs
#                       (dynamic models, test factories, etc.).
#   2. iter_concrete    Connects to subclasses already loaded at startup.
#
# dispatch_uid prevents duplicate connections if the app is reloaded.
#
# Refs: DD-009 (#9), DD-013 (#40), #44
# =============================================================================

from django.apps import AppConfig


class CladeConfig(AppConfig):
    name = "clade"
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    # django-stubs types default_auto_field as cached_property — known limitation.

    def ready(self) -> None:
        from django.db.models.signals import class_prepared, post_delete, post_save

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
        def iter_concrete(cls):
            for sub in cls.__subclasses__():
                if not sub._meta.abstract:
                    yield sub
                yield from iter_concrete(sub)

        for model in iter_concrete(CladeNode):
            connect(model)
