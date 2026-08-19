# =============================================================================
# clade/_discovery.py — Shared concrete-subclass discovery helper.
#
# Factored out of clade/apps.py (originally a local function inside
# CladeConfig.ready()) so that clade/affinity.py can reuse the same
# traversal for Meta.affinity_rules discovery, without duplicating the
# logic or importing apps.py at module level.
#
# Internal use only — not re-exported from clade/__init__.py.
#
# Refs: DD-005 (#5), DD-013 (#40)
# =============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from django.db.models import Model


def iter_concrete_subclasses(cls: type[Model]) -> Iterator[type[Model]]:
    """Yield every concrete (non-abstract) subclass of *cls*, recursively.

    Used to discover already-loaded concrete models at ``AppConfig.ready()``
    time — complements ``class_prepared`` for models declared afterwards
    (dynamic models, test factories).
    """
    for sub in cls.__subclasses__():
        if not sub._meta.abstract:  # type: ignore[reportAttributeAccessIssue]
            yield sub
        yield from iter_concrete_subclasses(sub)
