# =============================================================================
# clade/models.py — CladeNode abstract base class
#
# Provides the hierarchical backbone for all concrete models.
# The path field is managed by the module (post_save signal, #44).
# Do not write to path directly from user code.
#
# Refs: DD-001, DD-012, DD-013
#   https://gitlab.com/open-works/clade/-/issues/39  (DD-012)
#   https://gitlab.com/open-works/clade/-/issues/40  (DD-013)
#   https://gitlab.com/open-works/clade/-/issues/42  (this implementation)
# =============================================================================

from django.db import models


class CladeNode(models.Model):
    """Abstract base class for hierarchical (tree) models.

    Subclass this to create a concrete hierarchical model::

        class Department(CladeNode):
            name = models.CharField(max_length=255)

    The module manages all hierarchy behaviour — queries, path
    maintenance, deletion strategy.  User code focuses exclusively
    on domain fields.

    Fields
    ------
    parent : ForeignKey (self, nullable)
        Direct ancestor.  ``None`` for root nodes.
        ``on_delete`` is left to the concrete model (default: CASCADE).
        Override to use ``ADOPT`` (clade.deletion.ADOPT — #43).
    path : CharField
        Dot-separated integer PK chain representing the full ancestor
        path, e.g. ``"1.2.4.6"``.  Compatible with PostgreSQL ltree.
        Populated automatically by the post_save signal (#44).
        **Do not write directly.**

    Ordering
    --------
    Default ordering is by ``path``, which produces a consistent
    depth-first traversal on both SQLite and PostgreSQL backends.
    """

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
