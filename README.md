# Clade

> A Django module for managing hierarchical data models through a tree of nodes,
> with kinship relationship queries and optional database-native optimisations.

[![pipeline status](https://gitlab.com/open-works/clade/badges/main/pipeline.svg)](https://gitlab.com/open-works/clade/-/pipelines)
[![coverage](https://codecov.io/gl/open-works/clade/branch/main/graph/badge.svg)](https://codecov.io/gl/open-works/clade)
[![PyPI](https://img.shields.io/pypi/v/django-clade)](https://pypi.org/project/django-clade/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE.txt)

---

## Status

**Pre-alpha** — `v0.6.0` published. API not yet stable.

| Version | Status | Content                                                                                            |
|---|---|----------------------------------------------------------------------------------------------------|
| `v0.4.0` | ✅ Published | Extended kinship (pibling, nibling, cousin — symmetric degree)                                     |
| `v0.5.0` | ✅ Published | Affinity model & storage decision ([DD-005](https://gitlab.com/open-works/clade/-/work_items/5))   |
| `v0.6.0` | ✅ Current | Affinity transitivity & consistency ([DD-018](https://gitlab.com/open-works/clade/-/work_items/88)) |

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
attribute values without any hierarchical link between them — inter-model by
design, declared via `Meta.affinity_rules` *(v0.5.0)*.

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

## Affinity (v0.5.0, v0.6.0)

**Affinity** models a *non-hierarchical* relationship: two nodes that share an
attribute value, with no parent/child link between them. It's inter-model by
design — a `Department` and a `Project` can be in Affinity even though they're
unrelated concrete models, as long as both inherit `CladeNode`.

```python
from django.db import models
from clade.affinity import AffinityRule
from clade.models import CladeNode


class Department(CladeNode):
    name    = models.CharField(max_length=255)
    region  = models.CharField(max_length=255, null=True, blank=True)
    manager = models.CharField(max_length=255, null=True, blank=True)

    class Meta(CladeNode.Meta):
        affinity_rules = [
            AffinityRule("region",  to="myapp.Project", target_field="cost_center", channel="geo"),
            AffinityRule("manager", to="myapp.Project", target_field="lead",         channel="management"),
        ]


class Project(CladeNode):
    title       = models.CharField(max_length=255)
    cost_center = models.CharField(max_length=255, null=True, blank=True)
    lead        = models.CharField(max_length=255, null=True, blank=True)


# Affinity rows are materialised automatically on save — no manual sync.
paris_dept = Department.objects.create(name="Paris office", region="paris", manager="alice")
paris_proj = Project.objects.create(title="Metro extension", cost_center="paris", lead="alice")

paris_dept.affinities(channel="geo")         # QuerySet[Project] → [paris_proj]
paris_dept.affinities(channel="management")  # QuerySet[Project] → [paris_proj]

# Works from either side — a passive target model (Project here) never
# itself declares affinity_rules, but still resyncs on its own save.
paris_proj.affinities(channel="geo")         # QuerySet[Department] → [paris_dept]
```

`affinities(channel=None)` returns a single `QuerySet` and raises
`HeterogeneousAffinityError` if the result would span more than one partner
model — this can happen when two *different* source models reuse the same
channel name toward the same target (`channel` uniqueness is per declaring
model, not global). Use `affinities_grouped()` for that case: it never
raises, returning `{model: QuerySet}` instead of a single `QuerySet`.

```python
paris_dept.affinities_grouped(channel="geo")
# {Project: <QuerySet [paris_proj]>}
```

**Transitivity (v0.6.0):** by default only the relationships an `AffinityRule`
names directly are materialised. Two rules can be chained through a shared
model by opting in on *both* sides with `shared=True` — say `Department`'s
existing `"geo"` rule above gains `shared=True`, and `Project` gains a
second rule, reusing its own `cost_center`, onward to a new `Site` model:

```python
class Site(CladeNode):
    name   = models.CharField(max_length=255)
    region = models.CharField(max_length=255, null=True, blank=True)


# Department.Meta.affinity_rules — the existing "geo" rule, now consenting:
AffinityRule("region", to="myapp.Project", target_field="cost_center",
             channel="geo", shared=True)

# Project.Meta.affinity_rules — a new rule alongside the existing ones:
AffinityRule("cost_center", to="myapp.Site", target_field="region",
             channel="geo", shared=True)
```

With both ends consenting, `Department`↔`Site` is derived and stored
automatically (`Affinity.is_derived=True`) whenever `Department`↔`Project`
and `Project`↔`Site` share the same value under `"geo"`. One-sided consent
is rejected at `manage.py check` time (`clade.E003`), naming the model
where consent is incomplete. Derived pairs stay correct automatically as
data changes — deleting or changing the bridging instance recomputes them.

**Constraints:**
- `local_field`/`target_field` must be one of a fixed allowlist of scalar
  field types (`CharField`, `IntegerField`, `DateField`, `BooleanField`,
  and similar) — checked at `manage.py check` / CI startup (`clade.E002`).
  `ManyToManyField`, `FileField`, `JSONField`, `FloatField`, and
  `ForeignKey`/`OneToOneField` are rejected.
- `channel` must be unique within a single model's `affinity_rules` list
  (`clade.E001`) — but is freely reusable across different source models.
- Transitivity is opt-in, not automatic (`shared=True`, `clade.E003`) — see
  above.

See [issue #5](https://gitlab.com/open-works/clade/-/issues/5) (DD-005) and
[issue #88](https://gitlab.com/open-works/clade/-/issues/88) (DD-018) for
the full design rationale.

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
