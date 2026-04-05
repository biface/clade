# Clade

> Un module Django pour la gestion de modèles de données hiérarchiques sous forme
> d'arbre de nœuds, avec des requêtes de parenté et des optimisations natives
> selon le moteur de base de données.

[![statut pipeline](https://gitlab.com/open-works/clade/badges/main/pipeline.svg)](https://gitlab.com/open-works/clade/-/pipelines)
[![couverture](https://codecov.io/gl/open-works/clade/branch/main/graph/badge.svg)](https://codecov.io/gl/open-works/clade)
[![PyPI](https://img.shields.io/pypi/v/clade)](https://pypi.org/project/clade/)
[![Licence](https://img.shields.io/badge/licence-Apache%202.0-blue.svg)](LICENSE.txt)

---

## Statut

**Pré-développement** — `v0.0.5` en cours. Pas encore utilisable.

Voir les [jalons](https://gitlab.com/open-works/clade/-/milestones) et les [issues](https://gitlab.com/open-works/clade/-/issues) sur GitLab pour la feuille de route complète.

---

## Ce que ça fait

**Clade** fournit une application Django pour modéliser et interroger des données
structurées en arbre. Il expose l'ensemble des relations de parenté dérivables d'un
arbre de nœuds — pas seulement les paires parent/enfant, mais aussi les ascendants,
descendants, fratrie et lignes collatérales (piblings, niblings, cousins…) — avec
une terminologie non genrée tout au long.

Il introduit également le concept d'**Affinité** : une relation latérale entre des
nœuds partageant des valeurs d'attributs sans lien hiérarchique direct.

Le module cible plusieurs moteurs de base de données :
- **PostgreSQL** avec `ltree` — optimisation native (cible principale)
- **SQLite / autres** — implémentation de repli en Django pur

---

## Installation

> Pas encore publié. Les instructions seront ajoutées à `v0.1.0`.

```bash
pip install clade          # futur
```

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "clade",
]
```

---

## Prérequis

- Python 3.10+
- Django 5.2+

---

## Contribuer

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md) et [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

---

## Licence

Apache License 2.0 — voir [`LICENSE.txt`](LICENSE.txt) et [`NOTICE`](NOTICE).
