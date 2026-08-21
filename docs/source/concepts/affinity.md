# Affinity

Affinity is Clade's non-hierarchical counterpart to the tree: a relationship
between two nodes that share an attribute value, with **no** parent/child
link between them. Where {doc}`kinship` is entirely about position in the
tree, Affinity is entirely about shared data — the two are independent, and
a pair of nodes can be in Affinity regardless of where either sits in its
own tree, or even which concrete model each belongs to.

## Declaring a rule

Affinity relationships are declared with `AffinityRule` in `Meta`, the same
pattern Django itself uses for `Meta.constraints`:

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
```

Each `AffinityRule` names four things:

- **`local_field`** — the field on *this* model to match (`region`,
  `manager` above).
- **`to`** — the target model, as an `"app_label.Model"` string, resolved
  lazily so declaring a rule never forces an import between apps.
- **`target_field`** — the field on the target model to compare against.
  Always explicit, never inferred by matching field names — two unrelated
  models both happening to have a `name` field must never silently enter
  Affinity with each other.
- **`channel`** — a free-form label identifying the rule. It must be unique
  within one model's `affinity_rules` list (checked at `manage.py check`
  time, error `clade.E001`), but different models are free to reuse the
  same channel name toward the same target — that's what lets `Department`
  and some other model both declare a `"geo"` channel against `Project`
  without conflicting.

Only `CladeNode` subclasses can participate — a plain Django model declaring
`affinity_rules` without inheriting `CladeNode` isn't supported.

## Materialised, not computed on the fly

Affinity rows are stored, not calculated at query time. A single global
`Affinity` table (backed by `django.contrib.contenttypes`) holds one row per
matched pair, keeping every relationship queryable with a plain lookup
rather than a live scan. `post_save`/`post_delete` signals keep that table
in sync automatically — you never write to it directly:

```python
paris_dept = Department.objects.create(name="Paris office", region="paris", manager="alice")
paris_proj = Project.objects.create(title="Metro extension", cost_center="paris", lead="alice")

paris_dept.affinities(channel="geo")          # QuerySet[Project] → [paris_proj]
paris_dept.affinities(channel="management")   # QuerySet[Project] → [paris_proj]
```

This works from either side, including the side that never declared a rule
at all — `Project` here is a purely **passive target**: it appears only as
the `to=` of `Department`'s rules, yet saving a `Project` instance still
resynchronises the Affinity rows that reference it:

```python
paris_proj.affinities(channel="geo")          # QuerySet[Department] → [paris_dept]
```

That bidirectional coverage is deliberate. If only the declaring side
(`Department`) triggered recalculation, changing `Project.cost_center`
after the fact would leave a stale `Affinity` row pointing at the old
value — silently wrong until something touched `Department` again. Clade
avoids this by indexing both directions internally: which models declare
rules, and which models are named as a target by at least one rule. Saving
*either* side, in either role, keeps the table correct.

## Reading Affinity when the partner model isn't fixed

Because Affinity is inter-model by design, "the partners of this node"
isn't always a single, homogeneous queryset — two *different* source
models can legitimately reuse the same channel name toward the same
target. `affinities()` handles the common case and raises
`HeterogeneousAffinityError` if the result would actually span more than
one partner model; `affinities_grouped()` never raises, returning a dict
instead:

```python
paris_dept.affinities_grouped(channel="geo")
# {Project: <QuerySet [paris_proj]>}
```

Reach for `affinities_grouped()` whenever you can't guarantee in advance
that a channel maps to exactly one partner model.

## Constraints

- **`local_field`/`target_field` must be scalar**, drawn from an explicit
  allowlist (`CharField`, `TextField`, `SlugField`, `EmailField`,
  `URLField`, `GenericIPAddressField`, `UUIDField`, integer variants,
  `BooleanField`, `DateField`, `DateTimeField`, `TimeField`,
  `DurationField`, `DecimalField`) rather than a blacklist — an
  unrecognised or future field type is rejected by default. `ManyToManyField`,
  `FileField`/`ImageField`, `BinaryField`, `JSONField`, `FloatField`
  (epsilon-based equality is out of scope), and `ForeignKey`/`OneToOneField`
  (Affinity is defined *in opposition* to a structural link) are all
  rejected — error `clade.E002`, again checked at `manage.py check` time,
  never silently at write time.
- **`channel` uniqueness** is per declaring model, not global —
  `clade.E001`.
- **Matching is exact**, scoped to same channel and equal value. There's no
  fuzzy or normalised comparison beyond that.
- **Multi-hop transitivity is out of scope for this version.** If A and B
  share a value on some channel, and B and C share a value on that same
  channel, Clade does not currently infer that A and C are related too —
  only the relationships an `AffinityRule` explicitly names get
  materialised. Full transitive closure is planned for a later version.

## Where to go next

- {doc}`tree` and {doc}`kinship` — the hierarchical side of Clade, entirely
  independent of Affinity.
- {doc}`../reference/api` — full API reference, generated from source.
