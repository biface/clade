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

**Pré-alpha** — `v0.6.0` publié. L'API n'est pas encore stable.

| Version | Statut | Contenu                                                                                                 |
|---|---|---------------------------------------------------------------------------------------------------------|
| `v0.4.0` | ✅ Publiée | Parenté étendue (pibling, nibling, cousin — degré symétrique)                                           |
| `v0.5.0` | ✅ Publiée | Modèle Affinité & décision de stockage ([DD-005](https://gitlab.com/open-works/clade/-/work_items/5))   |
| `v0.6.0` | ✅ Actuelle | Transitivité et cohérence de l'Affinité ([DD-018](https://gitlab.com/open-works/clade/-/work_items/88)) |

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
nœuds partageant des valeurs d'attributs sans lien hiérarchique direct — inter-modèles
par conception, déclarée via `Meta.affinity_rules` *(v0.5.0)*.

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

## Affinité (v0.5.0, v0.6.0)

L'**Affinité** modélise une relation *non hiérarchique* : deux nœuds qui
partagent une valeur d'attribut, sans lien parent/enfant entre eux. Elle est
inter-modèles par conception — un `Department` et un `Project` peuvent être
en Affinité même s'ils sont des modèles concrets sans rapport entre eux, du
moment que les deux héritent de `CladeNode`.

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


# Les lignes d'Affinité sont matérialisées automatiquement à la sauvegarde —
# aucune synchronisation manuelle nécessaire.
paris_dept = Department.objects.create(name="Bureau de Paris", region="paris", manager="alice")
paris_proj = Project.objects.create(title="Extension du métro", cost_center="paris", lead="alice")

paris_dept.affinities(channel="geo")         # QuerySet[Project] → [paris_proj]
paris_dept.affinities(channel="management")  # QuerySet[Project] → [paris_proj]

# Fonctionne dans les deux sens — un modèle cible passif (Project ici) ne
# déclare jamais lui-même affinity_rules, mais se resynchronise quand même
# à sa propre sauvegarde.
paris_proj.affinities(channel="geo")         # QuerySet[Department] → [paris_dept]
```

`affinities(channel=None)` retourne un unique `QuerySet` et lève
`HeterogeneousAffinityError` si le résultat s'étendait sur plusieurs modèles
partenaires — ce cas peut survenir quand deux modèles sources *différents*
réutilisent le même nom de canal vers la même cible (l'unicité de `channel`
est par modèle déclarant, pas globale). Utilisez `affinities_grouped()` dans
ce cas : elle ne lève jamais d'exception et retourne `{modèle: QuerySet}` à
la place d'un `QuerySet` unique.

```python
paris_dept.affinities_grouped(channel="geo")
# {Project: <QuerySet [paris_proj]>}
```

**Transitivité (v0.6.0) :** par défaut, seules les relations explicitement
nommées par une `AffinityRule` sont matérialisées. Deux règles peuvent être
chaînées via un modèle partagé en y consentant explicitement, **des deux
côtés**, avec `shared=True` — disons que la règle `"geo"` existante de
`Department` ci-dessus gagne `shared=True`, et que `Project` gagne une
seconde règle, réutilisant son propre `cost_center`, vers un nouveau modèle
`Site` :

```python
class Site(CladeNode):
    name   = models.CharField(max_length=255)
    region = models.CharField(max_length=255, null=True, blank=True)


# Department.Meta.affinity_rules — la règle "geo" existante, qui consent désormais :
AffinityRule("region", to="myapp.Project", target_field="cost_center",
             channel="geo", shared=True)

# Project.Meta.affinity_rules — une nouvelle règle en plus des existantes :
AffinityRule("cost_center", to="myapp.Site", target_field="region",
             channel="geo", shared=True)
```

Une fois les deux extrémités consentantes, `Department`↔`Site` est dérivée
et stockée automatiquement (`Affinity.is_derived=True`) dès lors que
`Department`↔`Project` et `Project`↔`Site` partagent la même valeur sous
`"geo"`. Un consentement à sens unique est rejeté à `manage.py check`
(`clade.E003`), en nommant le modèle où le consentement est incomplet. Les
paires dérivées restent correctes automatiquement quand les données
changent — supprimer ou modifier l'instance pont les recalcule.

**Contraintes :**
- `local_field`/`target_field` doivent appartenir à une liste blanche fixe
  de types de champs scalaires (`CharField`, `IntegerField`, `DateField`,
  `BooleanField`, et similaires) — vérifié à `manage.py check` / au
  démarrage de la CI (`clade.E002`). `ManyToManyField`, `FileField`,
  `JSONField`, `FloatField`, et `ForeignKey`/`OneToOneField` sont rejetés.
- `channel` doit être unique au sein de la liste `affinity_rules` d'un même
  modèle (`clade.E001`) — mais librement réutilisable entre modèles sources
  différents.
- La transitivité est optionnelle, jamais automatique (`shared=True`,
  `clade.E003`) — voir ci-dessus.

Voir [l'issue #5](https://gitlab.com/open-works/clade/-/issues/5) (DD-005)
et [l'issue #88](https://gitlab.com/open-works/clade/-/issues/88) (DD-018)
pour la justification complète.

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
