# Kinship

Beyond parent/child pairs, Clade exposes the full set of relationships
derivable from the tree — ancestors, descendants, siblings, and collateral
lines like piblings, niblings, and cousins. Every term is gender-neutral
throughout the codebase and this documentation.

## Vocabulary

| Term | Meaning |
|---|---|
| `parent` | The direct ancestor of a node, one level up |
| `child` | A direct descendant of a node, one level down |
| `ancestor` | Any node on the path from a node to the root |
| `descendant` | Any node reachable downward from a node |
| `sibling` | A node sharing the same parent |
| `pibling` | A sibling of a node's parent (gender-neutral for aunt/uncle) |
| `nibling` | A child of a node's sibling (gender-neutral for nephew/niece) |
| `cousin` | A node sharing a common ancestor a fixed number of generations up |
| `root` | The topmost node of a tree (no parent) |
| `leaf` | A node with no children |

`pibling` and `nibling` aren't Clade inventions — they're established
gender-neutral terms already used in linguistics and social sciences, chosen
over `aunt/uncle` and `nephew/niece` to keep the vocabulary unambiguous
without defaulting to a gendered pair.

## Direct relationships

Every method below is available both as a queryset call and as a manager
call — use whichever fits the code you're writing:

```python
leaf.ancestors()                    # QuerySet, ordered by depth
leaf.descendants()
node.siblings()                     # excludes node itself

leaf.is_root                        # True if node has no parent
leaf.is_leaf                        # True if node has no children
leaf.root                           # the tree's root node

Category.objects.ancestors_of(leaf)
Category.objects.siblings_of(node)
```

`siblings()` returns an empty queryset for root nodes (no shared parent to
compare against) and for only-children — there's nothing to treat as an
error case here, both are ordinary tree shapes.

## Piblings and niblings

```python
me.piblings()          # siblings of my parent
aunt.niblings()        # children of my siblings, from aunt's perspective
```

Both are pure compositions of `siblings_of()` — no new SQL is introduced for
either. `piblings_of(node)` is `siblings_of(node.parent)`; `niblings_of(node)`
filters on `parent__in=siblings_of(node)`. As of the current version, both
use a **fixed degree only**: there's no "grand-pibling" (your grandparent's
sibling) or equivalent extended reach. A configurable-degree variant is
planned but not yet implemented.

## Cousins

Cousins don't reduce to a fixed-degree relationship the way piblings and
niblings do — genealogical cousinage is normally described with *two*
parameters, degree and "removed", and Clade deliberately does not implement
that full convention (see below). Instead, `cousins_of()` takes a single
`degree` parameter:

```python
me.cousins()                          # degree=2 by default: "1st cousin"
me.cousins(degree=3)                  # "2nd cousin"

Category.objects.cousins_of(me, degree=2)
```

`degree` counts how many levels above `node` the shared ancestor sits.
`degree=2` is the common case — nodes sharing a grandparent, excluding
siblings and piblings/niblings, which is what "1st cousin" means in
everyday usage. `degree=1` is a degenerate case that returns the same
result as `siblings_of()`.

### Why "symmetric degree" instead of the genealogical convention

The full genealogical convention pins down a cousin relationship with two
numbers: *degree* (how many generations back to the shared ancestor) and
*removed* (how many generations apart the two people themselves are — "1st
cousin once removed" means the shared ancestor is a grandparent for one
person and a great-grandparent for the other). That two-parameter,
asymmetric comparison doesn't reduce to the single-query pattern Clade uses
for `ancestors_of`/`descendants_of` — it would need a genuinely different
algorithm. `cousins_of()` instead uses **symmetric degree**: candidates must
sit at the *same* depth as `node`, sharing a common ancestor exactly
`degree` levels up from both. That's a smaller vocabulary than full
genealogical cousinage, but it reuses the same path-distance primitive
already powering the rest of Clade's queries, in a single SQL query on
either backend. The `removed` parameter is a possible future addition, not
something this version attempts.

### A cardinality note, not a bug

`cousins_of()` computes a pairwise relationship — if A and B are cousins,
that holds in both directions. But the *size* of the result set isn't
guaranteed to match between the two: on a tree where sibling branches have
different numbers of children, `cousins_of(D, degree=2)` and
`cousins_of(F, degree=2)` can return different numbers of results even
though `D` and `F` are cousins of each other in both directions. This is
expected behaviour under the symmetric-degree definition, not something to
work around.

## Where to go next

- {doc}`affinity` — a different kind of relationship entirely: nodes that
  share attribute values with no hierarchical link between them at all.
- {doc}`../reference/api` — full API reference, generated from source.
