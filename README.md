# Clade

> A Django module for managing hierarchical data models through a tree of nodes,
> with kinship relationship queries and optional database-native optimisations.

[![pipeline status](https://gitlab.com/open-works/clade/badges/main/pipeline.svg)](https://gitlab.com/open-works/clade/-/pipelines)
[![coverage](https://codecov.io/gl/open-works/clade/branch/main/graph/badge.svg)](https://codecov.io/gl/open-works/clade)
[![PyPI](https://img.shields.io/pypi/v/django-clade)](https://pypi.org/project/django-clade/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE.txt)

---

## Status

**Pre-development** — `v0.0.5` in progress. Not yet usable.

See the [milestones](https://gitlab.com/open-works/clade/-/milestones) and [open issues](https://gitlab.com/open-works/clade/-/issues) on GitLab for the full roadmap.

---

## What it does

**Clade** provides a Django application for modelling and querying tree-structured
data. It exposes the full set of kinship relationships derivable from a node tree —
not only parent/child pairs, but ancestors, descendants, siblings, and collateral
lines (piblings, niblings, cousins…) — using gender-neutral terminology throughout.

It also introduces **Affinity**: a lateral relationship between nodes that share
attribute values without any hierarchical link between them.

The module targets multiple database backends:
- **PostgreSQL** with `ltree` — native optimisation (primary target)
- **SQLite / other** — pure-Django fallback

---

## Install

> Not yet published. Instructions will be added at `v0.1.0`.

```bash
pip install clade          # future
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    "clade",
]
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
