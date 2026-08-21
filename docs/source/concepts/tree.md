# The Node Tree

Clade's primary data model is a **tree of nodes**: each node has one parent
and zero or more children, forming a hierarchy rooted at a single ancestor.
This page covers how that tree is represented, stored, and queried.

## The core concept

A tree in Clade is a directed acyclic graph where every node has at most one
parent. This is the natural shape for the data Clade was built for —
genealogy, org charts, taxonomies, category trees — and it maps cleanly onto
relational tables without needing a general graph model. Clade deliberately
does not support multiple parents per node; if your data needs that, it's
outside Clade's scope.

## `CladeNode`: one abstract class, zero configuration

You get a working tree by inheriting from `CladeNode` and adding your own
fields — nothing else:

```python
from django.db import models
from clade.models import CladeNode


class Department(CladeNode):
    name = models.CharField(max_length=255)
```

`CladeNode` is abstract, so `Department` gets its own database table, its
own migrations, and no shared state with any other model in your project.
Everything hierarchy-related — the `parent` field, the `path` field, query
methods, path maintenance on save and delete — comes from `CladeNode` and its
manager. You never define or touch `parent`/`path` yourself unless you need
custom `on_delete` behaviour (see [Deletion strategies](#deletion-strategies)
below).

## How the path is stored: Materialized Path

Each node stores its full ancestor chain as a dot-separated string of primary
keys — its **path**. For a small tree:

```
A (pk=1)                 → path = "1"
└── B (pk=2)              → path = "1.2"
    └── D (pk=4)           → path = "1.2.4"
        └── G (pk=6)        → path = "1.2.4.6"
```

Storing the full chain — rather than just a parent pointer — is what lets
ancestors, descendants, and depth-ordering resolve in a **single SQL query**,
with no recursive CTEs and no walking the tree in Python:

```python
# Descendants of a node
Category.objects.filter(path__startswith=node.path + ".")

# Ancestors of a node
parts = node.path.split(".")
Category.objects.filter(path__in=[".".join(parts[:i]) for i in range(1, len(parts))])

# Depth-ordered, consistently across backends
Category.objects.order_by("path")
```

The path is maintained automatically: creating or moving a node recalculates
its own path, and moving a node with descendants cascades the update to the
whole subtree — you never edit `path` by hand.

## One format, two backends

The materialized path format (dot-separated integer PKs) was chosen
specifically because it's compatible with PostgreSQL's `ltree` extension.
That lets Clade offer the same tree behind two different storage strategies
without changing your code:

| Backend | Field type | Path maintenance |
|---|---|---|
| SQLite (and other non-PostgreSQL backends) | plain `CharField` | Django `post_save` signal |
| PostgreSQL with `ltree` | `LtreeField` | database-native |

`LtreeField` is a small custom field (`clade/fields.py`) that extends
`CharField` and only overrides how it reports its column type: `ltree` on
PostgreSQL, ordinary `VARCHAR` everywhere else. Because the two are
API-compatible, the queries above — `path__startswith`, `path__in`,
`order_by("path")` — work unchanged regardless of which backend is
running underneath. Moving a project from SQLite to PostgreSQL is a schema
migration on `path`'s column type; nothing in your query code changes.

This mirrors Clade's general backend philosophy: use a database's native
tree support when it's available (PostgreSQL + `ltree`), and fall back to a
pure-Django implementation that still gives correct, single-query behaviour
everywhere else.

(deletion-strategies)=
## Deletion strategies

Deleting a node with children raises a question Clade doesn't answer for
you implicitly: what happens to those children? Two `on_delete` callables
are provided for the `parent` foreign key, so you choose per model:

- **`CASCADE`** (Django's built-in) — deletes the node and its entire
  subtree.
- **`ADOPT`** (Clade's own) — re-parents the deleted node's direct children
  to *its* parent (their grandparent), then deletes the node alone. The
  rest of each child's own subtree is untouched; only the immediate
  children move up one level.

```python
from clade.deletion import ADOPT


class Department(CladeNode):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=ADOPT,
        related_name="children",
    )
```

`ADOPT` is implemented as a proper `on_delete` callable — the same mechanism
Django uses for `CASCADE` and `SET_NULL` — rather than as an override of
`.delete()`. That distinction matters: overriding `.delete()` on the model
only catches deletion through a single instance; it's silently bypassed by
`QuerySet.delete()` (bulk deletion), which Django routes through the
`on_delete` callables directly. `ADOPT` works correctly either way.

If the deleted node is a root (no parent of its own), its children become
new roots. That's expected behaviour for `ADOPT`, not an error case to guard
against.

`ADOPT` is a good fit for organisational or category trees, where the
subtree below a deleted node should generally survive the deletion of one
level. Use `CASCADE` wherever the whole branch really should disappear with
its parent.

## Where to go next

- {doc}`kinship` — the relationship queries built on top of this tree:
  siblings, piblings, niblings, cousins.
- {doc}`affinity` — a non-hierarchical counterpart to everything on this
  page: relationships between nodes that share attribute values, with no
  parent/child link at all.
