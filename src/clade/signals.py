# =============================================================================
# clade/signals.py — Path maintenance signal handlers.
#
# Maintains the ``path`` field on all concrete CladeNode subclasses:
#
#   post_save   Recalculates path after create or reparent.
#               Cascades path update to all descendants on reparent.
#
#   post_delete Recalculates paths for nodes adopted by ADOPT callable.
#               Triggered after the FK bulk-update made by ADOPT.
#
# Signals are connected in CladeConfig.ready() (clade/apps.py).
# Using sender-specific connections via dispatch_uid prevents duplicate
# handler registration when the app is reloaded (e.g. in tests).
#
# Refs: DD-013 (#40), DD-014 (#41), #44
# =============================================================================


def _compute_path(instance) -> str:
    """Compute the materialized path for a CladeNode instance.

    Returns ``str(pk)`` for root nodes and
    ``parent.path + '.' + str(pk)`` for child nodes.

    Fetches the parent's path from the database to guarantee consistency
    even when the in-memory instance is stale.
    """
    if instance.parent_id is None:
        return str(instance.pk)

    parent = (
        type(instance)
        ._default_manager.filter(pk=instance.parent_id)
        .values("path")
        .first()
    )
    parent_path = parent["path"] if parent and parent["path"] else ""
    return f"{parent_path}.{instance.pk}" if parent_path else str(instance.pk)


def _update_subtree_paths(model, old_root_path: str, new_root_path: str) -> None:
    """Bulk-update paths for all descendants after a reparent.

    Replaces the ``old_root_path + '.'`` prefix with ``new_root_path + '.'``
    in the path of every descendant.  Processes nodes in path order
    (shallow before deep) so that each node's new path is correct when
    its own children are processed.

    Uses ``QuerySet.update()`` to avoid re-triggering ``post_save``.
    """
    old_prefix = old_root_path + "."
    new_prefix = new_root_path + "."

    descendants = model._default_manager.filter(path__startswith=old_prefix).order_by(
        "path"
    )
    for desc in descendants:
        new_path = new_prefix + desc.path[len(old_prefix) :]
        model._default_manager.filter(pk=desc.pk).update(path=new_path)


def on_cladenode_save(sender, instance, created, **kwargs) -> None:
    """Post-save: maintain the ``path`` field.

    Recalculates the path for the saved instance.  If the node was
    reparented (i.e. the path changed and the node is not new),
    cascades the path update to all descendants.

    Uses ``QuerySet.update()`` to avoid re-triggering ``post_save``
    and to update the database without loading the full instance.
    """
    old_path = instance.path
    new_path = _compute_path(instance)

    if new_path == old_path:
        return  # Nothing changed — skip DB write.

    # Persist the new path without re-triggering post_save.
    sender._default_manager.filter(pk=instance.pk).update(path=new_path)
    instance.path = new_path  # Keep in-memory instance consistent.

    if old_path and not created:
        # Node was reparented — cascade to descendants.
        _update_subtree_paths(sender, old_path, new_path)


def on_cladenode_delete(sender, instance, **kwargs) -> None:
    """Post-delete: recalculate paths for adopted descendants.

    Called after ``ADOPT`` has bulk-updated the FK on direct children.
    At this point the children's ``parent_id`` is correct (points to
    grandparent) but their ``path`` is still the old one.

    Processes nodes in path order (shallow before deep) so that each
    node's updated path is in the DB when its children are processed.
    """
    if not instance.path:
        return

    # All formerly-descendant nodes have stale paths.
    stale = list(
        sender._default_manager.filter(path__startswith=instance.path + ".").order_by(
            "path"
        )
    )
    for node in stale:
        new_path = _compute_path(node)
        if new_path != node.path:
            sender._default_manager.filter(pk=node.pk).update(path=new_path)
