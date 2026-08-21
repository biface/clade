# Quickstart

This guide walks through installing Clade and building your first node tree.
For the full API surface, see the {doc}`reference/api` page; for the concepts
behind what you see here, see {doc}`concepts/tree`, {doc}`concepts/kinship`,
and {doc}`concepts/affinity`.

## Install

```bash
pip install django-clade
```

Add `clade` to your project's installed apps:

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "django.contrib.contenttypes",  # required for Affinity, see concepts/affinity
    "clade",
]
```

Clade ships no models of its own to migrate — {class}`~clade.models.CladeNode`
is an abstract base class. You only run migrations for *your* models once you
define them below.

## Define your first model

Inherit from `CladeNode` and add whatever domain fields you need. No other
configuration is required — no explicit `parent` field, no path field, no
manager to wire up:

```python
from django.db import models
from clade.models import CladeNode


class Category(CladeNode):
    name = models.CharField(max_length=255)
```

Run the usual migration commands for your app (`makemigrations`, `migrate`).
`CladeNode` gives `Category` a `parent` foreign key and the machinery that
keeps a `path` in sync on every save — you never touch either directly.

## Build a tree

```python
root  = Category.objects.create(name="Root")
child = Category.objects.create(name="Child", parent=root)
leaf  = Category.objects.create(name="Leaf", parent=child)
```

Three nodes, one hierarchy: `root` → `child` → `leaf`.

## Traverse it

```python
leaf.ancestors()       # QuerySet → [root, child], ordered by depth
root.descendants()     # QuerySet → [child, leaf]
child.siblings()       # QuerySet → []

leaf.is_root            # False
leaf.is_leaf             # True
leaf.root                 # → root
```

Each of these resolves in a single SQL query, on every supported backend —
SQLite included. That's the point of the Materialized Path strategy
(see {doc}`concepts/tree`): no recursive queries, no Python-side loops over
the ORM.

The same operations are available from the manager, useful when you don't
already have an instance in hand:

```python
Category.objects.ancestors_of(leaf)
Category.objects.descendants_of(root)
```

## Where to go next

- {doc}`concepts/tree` — how the tree is actually stored (Materialized Path,
  the PostgreSQL `ltree` optimisation, and what changes between backends).
- {doc}`concepts/kinship` — the full relationship vocabulary: ancestors,
  descendants, siblings, piblings, niblings, and cousins.
- {doc}`concepts/affinity` — Affinity, the non-hierarchical counterpart to
  the tree: nodes that share attribute values without any parent/child link.
- {doc}`reference/api` — full API reference, generated from source.
