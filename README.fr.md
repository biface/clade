# Clade

> Un module Django pour la gestion de modèles de données hiérarchiques sous forme
> d'arbre de nœuds, avec des requêtes de parenté et des optimisations natives
> selon le moteur de base de données.

[![statut pipeline](https://gitlab.com/open-works/clade/badges/main/pipeline.svg)](https://gitlab.com/open-works/clade/-/pipelines)
[![couverture](https://codecov.io/gl/open-works/clade/branch/main/graph/badge.svg)](https://codecov.io/gl/open-works/clade)
[![PyPI](https://img.shields.io/pypi/v/django-clade)](https://pypi.org/project/django-clade/)
[![Licence](https://img.shields.io/badge/licence-Apache%202.0-blue.svg)](LICENSE.txt)

---

## Statut

**Pré-alpha** — `v0.4.0` publié. L'API n'est pas encore stable.

| Version | Statut | Contenu |
|---|---|---|
| `v0.4.0` | ✅ Actuelle | Parenté étendue (pibling, nibling, cousin — degré symétrique) |
| `v0.5.0` | 🔄 Suivante | Modèle Affinité & décision de stockage (DD-005) |

Voir les [jalons](https://gitlab.com/open-works/clade/-/milestones) et les
[issues](https://gitlab.com/open-works/clade/-/issues) sur GitLab pour la
feuille de route complète.

---

## Ce que ça fait

**Clade** fournit une application Django pour modéliser et interroger des données
structurées en arbre. Il expose l'ensemble des relations de parenté dérivables d'un
arbre de nœuds — pas seulement les paires parent/enfant, mais aussi les ascendants,
descendants, fratrie et lignes collatérales (piblings, niblings, cousins…) — avec
une terminologie non genrée tout au long.

Il introduit également le concept d'**Affinité** : une relation latérale entre des
nœuds partageant des valeurs d'attributs sans lien hiérarchique direct
*(prévu pour v0.5.0)*.

Le module cible plusieurs moteurs de base de données :
- **PostgreSQL** avec `ltree` — optimisation native *(v0.3.0)*
- **SQLite / autres** — implémentation de repli Materialized Path en Django pur *(actuel)*

---

## Installation

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

## Utilisation

```python
from clade.models import CladeNode
from django.db import models


class Categorie(CladeNode):
    nom = models.CharField(max_length=255)


# Construire un arbre
racine = Categorie.objects.create(nom="Racine")
enfant = Categorie.objects.create(nom="Enfant", parent=racine)
feuille = Categorie.objects.create(nom="Feuille", parent=enfant)

# Parcourir
feuille.ancestors()          # QuerySet → [racine, enfant]  (ordonné par path)
racine.descendants()         # QuerySet → [enfant, feuille]
enfant.siblings()            # QuerySet → []

feuille.is_root              # False
feuille.is_leaf              # True
feuille.root                 # → racine

# API Manager
Categorie.objects.ancestors_of(feuille)
Categorie.objects.descendants_of(racine)

# Stratégies de suppression
from clade.deletion import ADOPT

class Departement(CladeNode):
    nom = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=ADOPT,          # re-parentifie les enfants à la suppression
        related_name="children",
    )

# Parenté étendue (v0.4.0) — pibling, nibling, cousin
grandparent = Categorie.objects.create(nom="Grand-parent")
parent      = Categorie.objects.create(nom="Parent", parent=grandparent)
tante       = Categorie.objects.create(nom="Tante",  parent=grandparent)
moi         = Categorie.objects.create(nom="Moi",    parent=parent)
cousin      = Categorie.objects.create(nom="Cousin", parent=tante)

moi.piblings()                # QuerySet → [tante]     (fratrie de mon parent)
tante.niblings()               # QuerySet → [moi]       (enfants de sa fratrie)
moi.cousins()                  # QuerySet → [cousin]    (degree=2 par défaut)

# API Manager
Categorie.objects.piblings_of(moi)
Categorie.objects.cousins_of(moi, degree=2)
```

`cousins()`/`cousins_of()` utilisent un degré **symétrique**, et non la
convention généalogique `(degree, removed)` : `degree=2` (valeur par défaut)
correspond au "cousin germain" ; `degree=3` au "cousin issu de germain". Les
candidats à une profondeur différente du nœud lui-même (relation dite
"removed" en généalogie) ne sont pas couverts — voir
[l'issue #56](https://gitlab.com/open-works/clade/-/issues/56) pour la
justification complète et l'extension prévue post-v1.0.0.

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
