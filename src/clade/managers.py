# =============================================================================
# clade/managers.py — Hierarchy query methods for CladeNode.
#
# NodeQuerySet   Custom QuerySet with hierarchy traversal methods.
#                All methods return QuerySets (unordered by default).
#                Callers apply .order_by('path') when order matters.
#
# NodeManager    Manager that exposes NodeQuerySet methods at class level.
#
# Backend note
# ------------
# All methods use a single SQL query on SQLite via the ``path`` field.
# At v0.3.0, the PostgreSQL + ltree backend provides native equivalents
# with identical API and better performance at scale.
#
# Refs: DD-013 (#40), #45
# =============================================================================

from django.db import models


class NodeQuerySet(models.QuerySet):
    """QuerySet with hierarchy traversal for CladeNode subclasses."""

    # ── Traversal ─────────────────────────────────────────────────────────────

    def ancestors_of(self, node):
        """Return all ancestors of *node* (root to direct parent).

        Uses the materialized path to build an IN query — single SQL
        statement on both SQLite and PostgreSQL.

        Returns an **unordered** QuerySet; call ``.order_by('path')``
        for root-first ordering.

        Returns an empty QuerySet for root nodes (no ancestors).
        """
        if not node.path:
            return self.none()
        parts = node.path.split(".")
        ancestor_paths = [".".join(parts[:i]) for i in range(1, len(parts))]
        if not ancestor_paths:
            return self.none()
        return self.filter(path__in=ancestor_paths)

    def descendants_of(self, node):
        """Return all descendants of *node* (children, grandchildren, …).

        Uses a prefix search on the ``path`` field — single SQL statement.

        Returns an **unordered** QuerySet; call ``.order_by('path')``
        for depth-first ordering.

        Returns an empty QuerySet for leaf nodes.
        """
        if not node.path:
            return self.none()
        return self.filter(path__startswith=node.path + ".")

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
        if not node.path:
            return self.none()
        root_path = node.path.split(".")[0]
        return self.filter(path=root_path)


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
