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


class _AdoptCallable:
    """Re-parent direct children to grandparent before deletion.

    Implemented as a class so that ``deconstruct`` can be declared as a
    proper method — assigning attributes to a ``FunctionType`` is not
    allowed by strict type checkers.

    Use the module-level ``ADOPT`` singleton rather than instantiating
    this class directly.
    """

    def __call__(self, collector, field, sub_objs, using) -> None:  # noqa: D102
        if not sub_objs:
            return

        parent_pk = getattr(sub_objs[0], field.attname)
        parent_obj = field.related_model._default_manager.using(using).get(pk=parent_pk)
        grandparent_pk = getattr(parent_obj, field.attname)

        collector.add_field_update(field, grandparent_pk, sub_objs)

    def deconstruct(self):
        """Return the dotted import path for Django migration serialisation."""
        return ("clade.deletion.ADOPT", [], {})

    def __repr__(self) -> str:
        return "clade.deletion.ADOPT"


#: Singleton callable — use this in ForeignKey ``on_delete`` arguments.
ADOPT = _AdoptCallable()
