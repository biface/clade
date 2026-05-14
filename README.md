# Clade

> A Django module for managing hierarchical data models through a tree of nodes,
> with kinship relationship queries and optional database-native optimisations.

[![pipeline status](https://gitlab.com/open-works/clade/badges/main/pipeline.svg)](https://gitlab.com/open-works/clade/-/pipelines)
[![coverage](https://codecov.io/gl/open-works/clade/branch/main/graph/badge.svg)](https://codecov.io/gl/open-works/clade)
[![PyPI](https://img.shields.io/pypi/v/django-clade)](https://pypi.org/project/django-clade/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE.txt)

---

## Status

**Pre-alpha** — `v0.2.0` published. API not yet stable.

| Version | Status | Content |
|---|---|---|
| `v0.2.0` | ✅ Current | `CladeNode`, path maintenance, hierarchy queries, ADOPT deletion |
| `v0.3.0` | 🔄 Next | PostgreSQL + ltree backend |

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
```

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
