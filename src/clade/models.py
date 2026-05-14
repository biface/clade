# =============================================================================
# clade/models.py — CladeNode abstract base class.
#
# Refs: DD-001 (#1), DD-012 (#39), DD-013 (#40)
#   #42  model structure
#   #45  NodeManager wiring
#   #46  instance convenience methods
# =============================================================================

from __future__ import annotations

from django.db import models

from clade.managers import NodeManager


class CladeNode(models.Model):
    """Abstract base class for hierarchical (tree) models.

    Subclass this to create a concrete hierarchical model::

        class Department(CladeNode):
            name = models.CharField(max_length=255)

    The module manages all hierarchy behaviour — queries, path
    maintenance, and deletion strategy.  User code focuses exclusively
    on domain fields.

    Fields
    ------
    parent : ForeignKey (self, nullable)
        Direct ancestor.  ``None`` for root nodes.
        ``on_delete`` defaults to ``CASCADE``; override with
        ``clade.deletion.ADOPT`` to re-parent children on deletion.
    path : CharField
        Dot-separated integer PK chain (e.g. ``"1.2.4.6"``).
        Compatible with PostgreSQL ltree.
        Populated automatically by the post_save signal (clade.signals).
        **Do not write directly.**

    Manager
    -------
    ``objects`` is a ``NodeManager`` exposing hierarchy queries::

        Department.objects.ancestors_of(node)
        Department.objects.descendants_of(node)
        Department.objects.siblings_of(node)
        Department.objects.root_of(node)

    Instance methods
    ----------------
    Convenience wrappers that delegate to the manager::

        node.ancestors()    → QuerySet
        node.descendants()  → QuerySet
        node.siblings()     → QuerySet
        node.root           → single instance (property)
        node.is_root        → bool (property)
        node.is_leaf        → bool (property)

    Ordering
    --------
    Default ordering by ``path`` produces consistent depth-first
    traversal on SQLite and PostgreSQL backends.
    """

    objects = NodeManager()

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="parent",
    )
    path = models.CharField(
        max_length=255,
        blank=True,
        editable=False,
        db_index=True,
        verbose_name="materialized path",
        help_text=(
            "Dot-separated ancestor PK chain (e.g. '1.2.4'). "
            "Managed by the module — do not write directly."
        ),
    )

    class Meta:
        abstract = True
        ordering = ["path"]

    # ── Instance convenience methods (#46) ────────────────────────────────────

    def ancestors(self):
        """Return all ancestors as an unordered QuerySet.

        Delegates to ``type(self).objects.ancestors_of(self)``.
        Apply ``.order_by('path')`` for root-first ordering.
        """
        return type(self).objects.ancestors_of(self)

    def descendants(self):
        """Return all descendants as an unordered QuerySet.

        Delegates to ``type(self).objects.descendants_of(self)``.
        Apply ``.order_by('path')`` for depth-first ordering.
        """
        return type(self).objects.descendants_of(self)

    def siblings(self):
        """Return sibling nodes as a QuerySet (self excluded).

        Delegates to ``type(self).objects.siblings_of(self)``.
        """
        return type(self).objects.siblings_of(self)

    @property
    def root(self):
        """Return the root node of this tree (self if already root)."""
        return type(self).objects.root_of(self).get()

    @property
    def is_root(self) -> bool:
        """``True`` if this node has no parent."""
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        """``True`` if this node has no descendants."""
        return not type(self).objects.descendants_of(self).exists()
