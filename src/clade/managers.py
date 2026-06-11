# =============================================================================
# clade/managers.py — Hierarchy query methods for CladeNode.
#
# NodeQuerySet   Custom QuerySet with hierarchy traversal methods.
#                All methods return QuerySets (unordered by default).
#                Callers apply .order_by(field_name) when order matters.
#
# NodeManager    Manager that exposes NodeQuerySet methods at class level.
#
# Backend dispatch
# ----------------
# NodeQuerySet detects the active backend via connection.vendor and
# selects the appropriate query strategy:
#
#   PostgreSQL   Uses native ltree operators via LtreeField lookups:
#                  ancestors_of  → path @> node.path  (AncestorOf lookup)
#                  descendants_of → path <@ node.path  (DescendantOf lookup)
#
#   Other        Uses portable Django ORM queries:
#                  ancestors_of  → path__in=[list of ancestor paths]
#                  descendants_of → path__startswith=node.path + "."
#
# The dispatch is transparent to the caller — the public API is identical
# on all backends. The developer never interacts with connection.vendor.
#
# LtreeField detection
# --------------------
# NodeQuerySet locates the LtreeField dynamically via _path_field().
# This allows CladeNode subclasses to rename the field without breaking
# clade. Exactly one LtreeField per model is enforced at runtime.
#
# Refs: DD-003 (#3), DD-013 (#40), DD-015, #45
# =============================================================================

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.db import connection, models

from clade.fields import LtreeField


class NodeQuerySet(models.QuerySet):
    """QuerySet with hierarchy traversal for CladeNode subclasses."""

    # ── LtreeField detection ──────────────────────────────────────────────────

    def _path_field(self) -> LtreeField:
        """Return the unique LtreeField on this model.

        Locates the field dynamically so that CladeNode subclasses may
        rename it without breaking clade. Raises ``ImproperlyConfigured``
        if zero or more than one LtreeField is found.
        """
        assert self.model is not None  # noqa: S101
        ltree_fields = [
            f for f in self.model._meta.get_fields() if isinstance(f, LtreeField)
        ]
        if len(ltree_fields) == 0:
            raise ImproperlyConfigured(
                f"{self.model.__name__} has no LtreeField. "
                "CladeNode subclasses must not remove the path field."
            )
        if len(ltree_fields) > 1:
            raise ImproperlyConfigured(
                f"{self.model.__name__} has multiple LtreeField instances. "
                "Only one LtreeField is allowed per CladeNode subclass."
            )
        return ltree_fields[0]  # type: ignore[return-value]

    # ── Traversal ─────────────────────────────────────────────────────────────

    def ancestors_of(self, node):
        """Return all ancestors of *node* (root to direct parent).

        On PostgreSQL, uses the native ltree ``@>`` operator via the
        ``ancestor_of`` lookup registered on ``LtreeField``.

        On other backends, builds a Python list of ancestor paths and
        issues a single ``IN`` query.

        Returns an **unordered** QuerySet; call ``.order_by(field_name)``
        for root-first ordering.

        Returns an empty QuerySet for root nodes (no ancestors).
        """
        field = self._path_field()
        field_name: str = field.name  # type: ignore[assignment]
        node_path = getattr(node, field_name)
        if not node_path:
            return self.none()
        if connection.vendor == "postgresql":
            return self.filter(**{f"{field_name}__ancestor_of": node_path})
        parts = node_path.split(".")
        ancestor_paths = [".".join(parts[:i]) for i in range(1, len(parts))]
        if not ancestor_paths:
            return self.none()
        return self.filter(**{f"{field_name}__in": ancestor_paths})

    def descendants_of(self, node):
        """Return all descendants of *node* (children, grandchildren, …).

        On PostgreSQL, uses the native ltree ``<@`` operator via the
        ``descendant_of`` lookup registered on ``LtreeField``.

        On other backends, uses a prefix search on the path field —
        single SQL statement.

        Returns an **unordered** QuerySet; call ``.order_by(field_name)``
        for depth-first ordering.

        Returns an empty QuerySet for leaf nodes.
        """
        field = self._path_field()
        field_name: str = field.name  # type: ignore[assignment]
        node_path = getattr(node, field_name)
        if not node_path:
            return self.none()
        if connection.vendor == "postgresql":
            return self.filter(**{f"{field_name}__descendant_of": node_path})
        return self.filter(**{f"{field_name}__startswith": node_path + "."})

    def siblings_of(self, node):
        """Return nodes sharing the same parent as *node*.

        *node* itself is excluded from the result.

        Returns an empty QuerySet for root nodes (no common parent)
        and for only-children.
        """
        return self.filter(parent=node.parent).exclude(pk=node.pk)

    def root_of(self, node):
        """Return the root of the tree containing *node*.

        If *node* is already the root, returns a QuerySet containing
        *node* itself.
        """
        field = self._path_field()
        field_name: str = field.name  # type: ignore[assignment]
        node_path = getattr(node, field_name)
        if not node_path:
            return self.none()
        root_path = node_path.split(".")[0]
        return self.filter(**{field_name: root_path})


class NodeManager(models.Manager):
    """Manager that surfaces NodeQuerySet methods at the class level."""

    def get_queryset(self):
        return NodeQuerySet(self.model, using=self._db)

    # Proxy methods — enable ConcreteModel.objects.ancestors_of(node)

    def ancestors_of(self, node):
        return self.get_queryset().ancestors_of(node)

    def descendants_of(self, node):
        return self.get_queryset().descendants_of(node)

    def siblings_of(self, node):
        return self.get_queryset().siblings_of(node)

    def root_of(self, node):
        return self.get_queryset().root_of(node)
