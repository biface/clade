# Clade

A Django module for managing hierarchical data models through a tree of
nodes, with kinship relationship queries and optional database-native
optimisations.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
concepts/tree
concepts/kinship
concepts/affinity
reference/api
```

## What it does

**Clade** provides a Django application for modelling and querying
tree-structured data. It exposes the full set of kinship relationships
derivable from a node tree — not only parent/child pairs, but ancestors,
descendants, siblings, and collateral lines (piblings, niblings, cousins) —
using gender-neutral terminology throughout.

It also introduces **Affinity**: a lateral relationship between nodes that
share attribute values without any hierarchical link between them.

## Install

```bash
pip install django-clade
```

See {doc}`quickstart` to get started.
