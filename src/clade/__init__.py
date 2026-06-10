"""django-clade — hierarchical data models for Django.

Public API
----------
CladeNode               Abstract base class for hierarchical models.
ADOPT                   Custom on_delete callable — re-parents children on
                        deletion.
LtreeField              Path field — ltree on PostgreSQL, VARCHAR elsewhere.
ConditionalAlterField   Migration operation — AlterField on supported backends
                        only.

Refs: DD-008 (#8), DD-012 (#39), DD-014 (#41), DD-015
"""

from clade.deletion import ADOPT
from clade.fields import ConditionalAlterField, LtreeField

__all__ = ["ADOPT", "LtreeField", "ConditionalAlterField"]
