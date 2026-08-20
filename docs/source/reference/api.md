# API Reference

This page is generated from source docstrings via `sphinx.ext.autodoc` and
`sphinx.ext.napoleon` (DD-017). It documents Clade's public surface only —
internal wiring (signal registration, `django.core.checks` hooks,
PostgreSQL-only lookup/expression classes) is deliberately left out; see the
narrative guides ({doc}`../concepts/tree`, {doc}`../concepts/kinship`,
{doc}`../concepts/affinity`) for how those pieces fit together.

## Tree & hierarchy

### CladeNode

```{eval-rst}
.. autoclass:: clade.models.CladeNode
   :members:
   :show-inheritance:
```

### Manager and QuerySet

```{eval-rst}
.. autoclass:: clade.managers.NodeManager
   :members:
   :show-inheritance:

.. autoclass:: clade.managers.NodeQuerySet
   :members:
   :show-inheritance:
```

### Deletion

```{eval-rst}
.. autodata:: clade.deletion.ADOPT
   :no-value:
```

### Fields

```{eval-rst}
.. autoclass:: clade.fields.LtreeField
   :members:
   :show-inheritance:

.. autoclass:: clade.fields.ConditionalAlterField
   :members:
   :show-inheritance:
```

## Affinity

### Declaration

```{eval-rst}
.. autoclass:: clade.affinity.AffinityRule
   :members:
```

### Storage

```{eval-rst}
.. autoclass:: clade.affinity.Affinity
   :members:
   :show-inheritance:
```

### Querying

```{eval-rst}
.. autofunction:: clade.affinity.affinities_of

.. autofunction:: clade.affinity.affinities_of_grouped

.. autoexception:: clade.affinity.HeterogeneousAffinityError
```
