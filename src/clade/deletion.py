# =============================================================================
# clade/deletion.py — Custom on_delete callables for CladeNode.
#
# Provides:
#     ADOPT   Re-parents direct children to grandparent before deletion.
#             Works with both instance.delete() and QuerySet.delete()
#             because it is a proper on_delete callable, not a delete()
#             override.
#
# Usage::
#
#     from clade.deletion import ADOPT
#
#     class Department(CladeNode):
#         parent = models.ForeignKey(
#             'self',
#             null=True,
#             blank=True,
#             on_delete=ADOPT,
#             related_name='children',
#         )
#
# Refs: DD-014 (#41), #43
# =============================================================================


def ADOPT(collector, field, sub_objs, using):
    """Re-parent direct children to grandparent before deletion.

    When a CladeNode is deleted with ``on_delete=ADOPT``, its direct
    children are re-parented to the deleted node's own parent
    (the grandparent) rather than being cascaded or orphaned.

    If the deleted node is a root (``parent=None``), its children
    become new roots (``parent=None``).  This is documented behaviour,
    not an error.

    Path recalculation for adopted nodes is handled by the
    ``post_delete`` signal registered in ``clade.apps`` (#44).

    Parameters
    ----------
    collector : django.db.models.deletion.Collector
        Accumulates the DB operations for this deletion.
    field : django.db.models.fields.related.ForeignKey
        The ``parent`` ForeignKey pointing to the node being deleted.
    sub_objs : QuerySet
        Direct children of the node being deleted.
    using : str
        Database alias.
    """
    if not sub_objs:
        return

    # All sub_objs share the same parent (the node being deleted).
    # We recover the grandparent from the first child's parent FK value.
    parent_pk = getattr(sub_objs[0], field.attname)
    parent_obj = field.related_model._default_manager.using(using).get(pk=parent_pk)
    grandparent_pk = getattr(parent_obj, field.attname)  # None if root

    # Bulk-update the FK on all direct children.
    # Path recalculation is deferred to the post_delete signal.
    collector.add_field_update(field, grandparent_pk, sub_objs)


# Required for Django migration serialisation.
# Allows makemigrations to reconstruct the callable from its dotted path.
ADOPT.deconstruct = lambda: ("clade.deletion.ADOPT", [], {})
