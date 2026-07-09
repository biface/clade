# Clade

> A Django module for managing hierarchical data models through a tree of nodes,
> with kinship relationship queries and optional database-native optimisations.

[![pipeline status](https://gitlab.com/open-works/clade/badges/main/pipeline.svg)](https://gitlab.com/open-works/clade/-/pipelines)
[![coverage](https://codecov.io/gl/open-works/clade/branch/main/graph/badge.svg)](https://codecov.io/gl/open-works/clade)
[![PyPI](https://img.shields.io/pypi/v/django-clade)](https://pypi.org/project/django-clade/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE.txt)

---

## Status

**Pre-alpha** — `v0.4.0` published. API not yet stable.

| Version | Status | Content |
|---|---|---|
| `v0.4.0` | ✅ Current | Extended kinship (pibling, nibling, cousin — symmetric degree) |
| `v0.5.0` | 🔄 Next | Affinity model & storage decision (DD-005) |

See the [milestones](https://gitlab.com/open-works/clade/-/milestones) and
[open issues](https://gitlab.com/open-works/clade/-/issues) on GitLab for the
full roadmap.

---

## What it does

**Clade** provides a Django application for modelling and querying tree-structured
data. It exposes the full set of kinship relationships derivable from a node tree —
not only parent/child pairs, but ancestors, descendants, siblings, and collateral
lines (piblings, niblings, cousins…) — using gender-neutral terminology throughout.

It also introduces **Affinity**: a lateral relationship between nodes that share
attribute values without any hierarchical link between them *(planned for v0.5.0)*.

The module targets multiple database backends:
- **PostgreSQL** with `ltree` — native optimisation *(v0.3.0)*
- **SQLite / other** — pure-Django Materialized Path fallback *(current)*

---

## Install

```bash
pip install django-clade
```

```python, ignore
# settings.py
INSTALLED_APPS = [
    ...
    "clade",
]
```

---

## Usage

```python
from clade.models import CladeNode
from django.db import models


class Category(CladeNode):
    name = models.CharField(max_length=255)


# Build a tree
root  = Category.objects.create(name="Root")
child = Category.objects.create(name="Child", parent=root)
leaf  = Category.objects.create(name="Leaf",  parent=child)

# Traverse
leaf.ancestors()             # QuerySet → [root, child]  (ordered by path)
root.descendants()           # QuerySet → [child, leaf]
child.siblings()             # QuerySet → []

leaf.is_root                 # False
leaf.is_leaf                 # True
leaf.root                    # → root

# Manager API
Category.objects.ancestors_of(leaf)
Category.objects.descendants_of(root)

# Deletion strategies
from clade.deletion import ADOPT

class Department(CladeNode):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=ADOPT,          # re-parents children on delete
        related_name="children",
    )

# Extended kinship (v0.4.0) — pibling, nibling, cousin
grandparent = Category.objects.create(name="Grandparent")
parent      = Category.objects.create(name="Parent", parent=grandparent)
aunt        = Category.objects.create(name="Aunt",   parent=grandparent)
me          = Category.objects.create(name="Me",     parent=parent)
cousin      = Category.objects.create(name="Cousin", parent=aunt)

me.piblings()                 # QuerySet → [aunt]      (siblings of my parent)
aunt.niblings()               # QuerySet → [me]        (children of my siblings)
me.cousins()                  # QuerySet → [cousin]    (degree=2, the default)

# Manager API
Category.objects.piblings_of(me)
Category.objects.cousins_of(me, degree=2)
```

`cousins()`/`cousins_of()` use a **symmetric** degree, not the genealogical
`(degree, removed)` convention: `degree=2` (the default) matches "1st cousin";
`degree=3` matches "2nd cousin". Candidates at a different depth than the
node itself (genealogically "once removed", etc.) are not covered — see
[issue #56](https://gitlab.com/open-works/clade/-/issues/56) for the full
rationale and the planned post-v1.0.0 extension.

---

## Requirements

- Python 3.10+
- Django 5.2+

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

---

## Licence

Apache License 2.0 — see [`LICENSE.txt`](LICENSE.txt) and [`NOTICE`](NOTICE).
