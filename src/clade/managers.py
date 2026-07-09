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
# Refs: DD-003 (#3), DD-013 (#40), DD-015, DD-016 (#56), #45
# =============================================================================

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.db import connection, models
from django.db.models import Value
from django.db.models.functions import Length, Replace

from clade.fields import LtreeField, NLevel


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
            return self.filter(**{f"{field_name}__ancestor_of": node_path}).exclude(
                pk=node.pk
            )
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
            return self.filter(**{f"{field_name}__descendant_of": node_path}).exclude(
                pk=node.pk
            )
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

    # ── Extended kinship (DD-016, #56) ────────────────────────────────────────

    def piblings_of(self, node):
        """Return siblings of *node*'s parent (gender-neutral aunt/uncle).

        Fixed degree only in v0.4.0 — no "grand-pibling" (see DD-016).
        Delegates entirely to ``siblings_of()``; introduces no new SQL.

        Returns an empty QuerySet if *node* is a root (no parent).
        """
        if node.parent_id is None:
            return self.none()
        return self.siblings_of(node.parent)

    def niblings_of(self, node):
        """Return children of *node*'s siblings (gender-neutral nephew/niece).

        Fixed degree only in v0.4.0 (see DD-016). Implemented as
        ``filter(parent__in=siblings_of(node))`` — introduces no new SQL
        beyond the existing ``siblings_of()`` primitive.

        Returns an empty QuerySet if *node* has no siblings, or if none
        of *node*'s siblings have children.
        """
        return self.filter(parent__in=self.siblings_of(node))

    def cousins_of(self, node, degree: int = 2):
        """Return nodes sharing a common ancestor exactly *degree* levels
        above *node*, at the same depth as *node* (**symmetric degree**,
        not genealogical ``degree``/``removed`` — see DD-016).

        ``degree=2`` corresponds to genealogical "1st cousin"; ``degree=3``
        to "2nd cousin". ``degree=1`` is degenerate and returns the same
        set as ``siblings_of()``.

        This definition is symmetric: it does **not** cover genealogical
        "removed" cousins (candidates at a different depth than *node*
        that share a common ancestor at an equivalent distance). That
        parameter is deferred to post-v1.0.0 (see DD-016).

        Returns an empty QuerySet if *node* has no ancestor *degree*
        levels up (i.e. *node* is too close to the root).

        Raises
        ------
        ValueError
            If *degree* is less than 1.
        """
        if degree < 1:
            raise ValueError(f"degree must be >= 1, got {degree!r}")

        field = self._path_field()
        field_name: str = field.name  # type: ignore[assignment]
        node_path = getattr(node, field_name)
        if not node_path:
            return self.none()

        parts = node_path.split(".")
        if len(parts) <= degree:
            return self.none()

        ancestor_path = ".".join(parts[: len(parts) - degree])
        closer_ancestor_path = (
            node_path if degree == 1 else ".".join(parts[: len(parts) - (degree - 1)])
        )

        if connection.vendor == "postgresql":
            # descendant_of (<@) is inclusive (DD-015 / #55 bugfix): excluding
            # descendants of closer_ancestor_path also removes closer_ancestor_path
            # itself and node's own branch — no separate self-exclusion needed.
            return (
                self.filter(**{f"{field_name}__descendant_of": ancestor_path})
                .exclude(**{f"{field_name}__descendant_of": closer_ancestor_path})
                .annotate(_nlevel=NLevel(field_name))
                .filter(_nlevel=len(parts))
            )

        # Fallback: __startswith is exclusive of the prefix itself, so the
        # degree == 1 case (closer_ancestor_path == node_path) needs an
        # explicit equality exclusion to remove node itself.
        return (
            self.filter(**{f"{field_name}__startswith": ancestor_path + "."})
            .exclude(**{f"{field_name}__startswith": closer_ancestor_path + "."})
            .exclude(**{field_name: closer_ancestor_path})
            .annotate(
                _dots=Length(field_name)
                - Length(Replace(field_name, Value("."), Value(""))),
            )
            .filter(_dots=len(parts) - 1)
        )


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

    def piblings_of(self, node):
        return self.get_queryset().piblings_of(node)

    def niblings_of(self, node):
        return self.get_queryset().niblings_of(node)

    def cousins_of(self, node, degree: int = 2):
        return self.get_queryset().cousins_of(node, degree=degree)
