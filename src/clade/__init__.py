"""django-clade — hierarchical data models for Django.

Public API
----------
CladeNode   Abstract base class for hierarchical models.
ADOPT       Custom on_delete callable — re-parents children on deletion.

Refs: DD-008 (#8), DD-012 (#39), DD-014 (#41)
"""

from clade.deletion import ADOPT

__all__ = ["ADOPT"]
