# =============================================================================
# clade/fields.py — Custom field types for CladeNode.
#
# LtreeField          Stores the materialized path as PostgreSQL ltree on
#                     PostgreSQL, and as VARCHAR on all other backends.
#                     API and query patterns (startswith, path__in) are
#                     identical across backends — only the DDL differs.
#
#                     Registers two PostgreSQL-native lookups:
#                       - descendant_of  →  path <@ rhs
#                       - ancestor_of    →  path @> rhs
#                     These lookups are used exclusively by NodeQuerySet
#                     on PostgreSQL. They are never called on other backends.
#
# ConditionalAlterField
#                     Migration operation that executes an AlterField only
#                     on backends that support the target field type.
#                     Used whenever a LtreeField is involved in a migration,
#                     so that SQLite and other backends are unaffected.
#
# Refs: DD-003 (#3), DD-013 (#40), DD-015
# =============================================================================

from __future__ import annotations

from typing import Literal

from django.db import migrations, models
from django.db.models import Lookup


class LtreeField(models.CharField):
    """Materialized path field — ltree on PostgreSQL, VARCHAR elsewhere.

    Extends ``CharField`` so that all Django ORM lookups (``startswith``,
    ``in``, ``exact``) work transparently on every backend without
    modification to ``NodeQuerySet``.

    On PostgreSQL, ``db_type()`` returns ``"ltree"``, enabling:

    - Native ltree indexing (GiST / GIN) — activated at v0.8.0.
    - Native ltree operators in ``NodeQuerySet`` — introduced at v0.3.0.

    On all other backends (SQLite, MySQL, …), the field behaves as a
    plain ``VARCHAR``.

    Exactly one ``LtreeField`` is allowed per ``CladeNode`` subclass.
    ``NodeQuerySet`` locates it dynamically via ``_meta.get_fields()``
    so the field may be renamed in subclasses without breaking clade.

    Usage
    -----
    Declared once on ``CladeNode.path`` — managed by the module.
    Do not instantiate directly in user code.
    """

    def db_type(self, connection) -> str:
        """Return the database column type.

        Returns ``"ltree"`` on PostgreSQL; delegates to ``CharField``
        (i.e. ``VARCHAR(max_length)``) on all other backends.
        """
        if connection.vendor == "postgresql":
            return "ltree"
        result = super().db_type(connection)
        assert isinstance(result, str)  # noqa: S101  (CharField always returns str)
        return result

    def get_internal_type(self) -> Literal["CharField"]:
        """Report as CharField for cross-backend compatibility.

        Returning ``"CharField"`` ensures Django can resolve the correct
        SQL column type on every backend via its ``data_types`` registry.
        On non-PostgreSQL backends the field is stored as VARCHAR; on
        PostgreSQL ``db_type()`` overrides this with ``"ltree"``.

        Migration detection (``makemigrations``) relies on ``db_type()``
        returning ``"ltree"`` on PostgreSQL, not on ``get_internal_type()``.
        """
        return "CharField"

    def deconstruct(self):
        """Return field deconstruction for migration serialisation.

        Overrides the path to ``clade.fields.LtreeField`` so that
        generated migrations import from the correct location.
        """
        name, path, args, kwargs = super().deconstruct()
        path = "clade.fields.LtreeField"
        return name, path, args, kwargs


# =============================================================================
# PostgreSQL-native ltree lookups — used exclusively by NodeQuerySet.
#
# These lookups translate directly to ltree operators and contain no
# Python-level logic. The backend dispatch (when to use them vs the
# fallback strategies) is the sole responsibility of NodeQuerySet.
#
# DescendantOf  path <@ rhs   — "is path a descendant of rhs?"
# AncestorOf    path @> rhs   — "is path an ancestor of rhs?"
# =============================================================================


class DescendantOf(Lookup):
    """PostgreSQL ltree lookup: path <@ rhs (path is descendant of rhs).

    Used by ``NodeQuerySet.descendants_of()`` on PostgreSQL only.
    Never call this lookup directly — use ``NodeQuerySet`` instead.
    """

    lookup_name = "descendant_of"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"{lhs} <@ {rhs}", lhs_params + rhs_params


class AncestorOf(Lookup):
    """PostgreSQL ltree lookup: path @> rhs (path is ancestor of rhs).

    Used by ``NodeQuerySet.ancestors_of()`` on PostgreSQL only.
    Never call this lookup directly — use ``NodeQuerySet`` instead.
    """

    lookup_name = "ancestor_of"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"{lhs} @> {rhs}", lhs_params + rhs_params


LtreeField.register_lookup(DescendantOf)
LtreeField.register_lookup(AncestorOf)


class ConditionalAlterField(migrations.AlterField):
    """Migration operation that alters a field only on supported backends.

    Wraps Django's ``AlterField`` and skips the DDL entirely on backends
    that do not support the target field type (e.g. SQLite when the target
    is ``LtreeField``).

    The migration graph remains consistent on all backends — Django records
    the operation as applied — but only the supported backends receive the
    actual schema change.

    This is the correct operation to use whenever a ``LtreeField`` appears
    in a migration, ensuring that:

    - PostgreSQL receives ``ALTER COLUMN path TYPE ltree USING path::ltree``.
    - SQLite and other backends skip the DDL without error or table recreation.

    Usage
    -----
    In any migration involving a ``LtreeField``::

        from clade.fields import ConditionalAlterField, LtreeField

        class Migration(migrations.Migration):
            operations = [
                ConditionalAlterField(
                    model_name="department",
                    name="path",
                    field=LtreeField(
                        max_length=255,
                        blank=True,
                        editable=False,
                        db_index=True,
                    ),
                ),
            ]

    Parameters
    ----------
    vendors : tuple[str, ...]
        Database vendor names on which the operation is executed.
        Defaults to ``("postgresql",)``.
        Pass additional vendors if future backends gain ltree support.
    """

    def __init__(self, *args, vendors: tuple[str, ...] = ("postgresql",), **kwargs):
        self.vendors = vendors
        super().__init__(*args, **kwargs)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Execute the AlterField only on supported backends."""
        if schema_editor.connection.vendor in self.vendors:
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Reverse the AlterField only on supported backends."""
        if schema_editor.connection.vendor in self.vendors:
            super().database_backwards(app_label, schema_editor, from_state, to_state)

    def deconstruct(self):
        """Return operation deconstruction for migration serialisation."""
        name, args, kwargs = super().deconstruct()
        if self.vendors != ("postgresql",):
            kwargs["vendors"] = self.vendors
        return name, args, kwargs

    def describe(self) -> str:  # type: ignore[override]
        """Return a human-readable description for ``showmigrations``."""
        vendors = ", ".join(self.vendors)
        return f"{super().describe()} (conditional on: {vendors})"
