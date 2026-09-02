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
            AffinityRule("manager", to="myapp.Project", target_field="lead", channel="management"),
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

## Transitivity: chaining through a shared model

By default, only the relationships an `AffinityRule` explicitly names get
materialised. If `Department` declares a rule toward `Project`, and
`Project` separately declares its own rule toward `Site`, that's two
*direct* relationships — `Department`↔`Project` and `Project`↔`Site` — with
nothing connecting `Department` and `Site` on its own.

Sometimes that's exactly what you want: two declared relationships happening
to reuse the same channel name toward a common model is not, by itself, a
signal that they should be treated as one chain. A `channel` name is
free-form text; two independently-authored rules can collide on it by
coincidence. So Clade never infers a chain automatically — extending
Affinity across a shared model is something you opt into explicitly, per
rule, with `shared=True`. Say a new `Site` model joins the picture:

```python
from django.db import models
from clade.affinity import AffinityRule
from clade.models import CladeNode

class Site(CladeNode):
    name   = models.CharField(max_length=255)
    region = models.CharField(max_length=255, null=True, blank=True)
```

Both ends of the shared model then opt in — `Department`'s existing `"geo"`
rule toward `Project` gains `shared=True`, and `Project` gains a *second*
rule, alongside its existing ones, linking onward to `Site` under that same
channel name:

```python
# Department.Meta.affinity_rules — the existing "geo" rule from above,
# now consenting to be used as a link:
AffinityRule(
    "region", to="myapp.Project", target_field="cost_center",
    channel="geo", shared=True,
)

# Project.Meta.affinity_rules — a new rule alongside cost_center's own,
# reusing cost_center again as the value to match against Site.region:
AffinityRule(
    "cost_center", to="myapp.Site", target_field="region",
    channel="geo", shared=True,
)
```

With both ends of the shared model (`Project`) opting in under the same
`channel` name, a `paris_dept`↔`paris_proj` pair and a `paris_proj`↔`paris_site`
pair — both channel `"geo"`, both matching on the value `"paris"` — imply a
third pair, `paris_dept`↔`paris_site`, computed and stored automatically:

```python
paris_dept.affinities(channel="geo")   # QuerySet[Project | Site] → includes paris_site, not just paris_proj
```

**Consent must be symmetric.** `shared=True` on `Department`'s rule alone
isn't enough — `Project`'s rule toward `Site` must *also* carry
`shared=True` for the chain to form. One-sided consent is rejected at
`manage.py check` time (error `clade.E003`), naming the model where consent
is incomplete. This is deliberate: `shared=True` is a statement that *this*
relationship may be used as a link in someone else's chain, and that
statement only means something when made on both sides of the link.
Two rules that happen to reuse a channel name toward a common model but
where neither (or only one) opts in stay exactly as direct-only as they
were before — reusing a channel name is always safe on its own; only a
model actually caught between two consenting rules ever needs to decide.

Chains aren't limited to two hops. If a third rule links `Site` onward to
`Building` under the same channel, again with mutual `shared=True` consent,
`Department`, `Project`, `Site`, and `Building` all end up affine with one
another — and a cycle of consenting relationships closes into one fully
connected group rather than a simple chain, the same way any transitive
relationship would.

```{note}
Why not simply treat *any* two rows sharing a `(channel, value)` pair as
transitively related, with no opt-in at all? Because that reopens exactly
the false-positive risk `target_field`'s explicit mapping was designed to
close in the first place — two unrelated rules coincidentally using the
same channel name would silently merge into one group. Requiring consent at
the specific model where two rules actually meet keeps that risk scoped to
a deliberate decision instead of a naming coincidence.
```

```{warning}
`clade.E003` checks *structural* consistency — that every rule touching a
shared model under a channel name agrees — not semantic intent end to end.
`shared=True` is a per-model, per-channel switch that accumulates: a later,
unrelated `AffinityRule` reusing the same channel name and also consenting
at that same model can silently extend a chain further than any one
developer, looking only at the rule they're adding, could anticipate. This
is expected behaviour, not a bug — auditing whether a resulting chain is
actually business-appropriate is your responsibility, the same way it
already is for any other cross-cutting naming choice in a shared codebase.
```

Derived pairs live in the same `Affinity` table as direct ones — there's no
separate model, and `affinities()`/`affinities_grouped()` return both
together by default. They're kept correct automatically as data changes:
deleting a bridging instance drops derived pairs that depended on it
(recreating any that are still reachable through a different consenting
model), and changing a value away from what a chain shared does the same.

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
- **Transitivity is opt-in, not automatic.** If A and B share a value on
  some channel, and B and C share a value on that same channel, Clade only
  infers that A and C are related too when the model at B has consented on
  both sides via `shared=True` — see "Transitivity: chaining through a
  shared model" above. Without that consent, only the relationships an
  `AffinityRule` explicitly names get materialised, exactly as before.

## Where to go next

- {doc}`tree` and {doc}`kinship` — the hierarchical side of Clade, entirely
  independent of Affinity.
- {doc}`../reference/api` — full API reference, generated from source.
