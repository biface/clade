# Contribuer à Clade

Merci de votre intérêt pour le projet. Ce document explique comment configurer
l'environnement de développement et soumettre des modifications.

---

## Prérequis

- Python 3.10 ou supérieur
- [uv](https://github.com/astral-sh/uv) pour la gestion de l'environnement virtuel
- [tox](https://tox.wiki/) + [tox-uv](https://github.com/tox-dev/tox-uv)
- PyCharm est l'IDE recommandé, mais tout éditeur convient

Pour les tests d'intégration uniquement :

- Une instance PostgreSQL (≥ 14) avec l'extension `ltree` activée
- Une base de données et un utilisateur dédiés (voir [Tests d'intégration](#tests-dintégration) ci-dessous)

---

## Mise en place de l'environnement

```bash
git clone git@gitlab.com:open-works/clade.git
cd clade
uv venv
uv sync --extra dev
```

---

## Lancer les vérifications en local

Toutes les vérifications qualité sont orchestrées par tox :

```bash
tox -e pre-push     # chaîne complète : format + qualité + tests + couverture
tox -e flake8       # flake8 — lint
tox -e black-check  # black — vérification du format
tox -e isort-check  # isort — vérification de l'ordre des imports
tox -e basedpyright # basedpyright — vérification des types
tox -e bandit       # bandit — analyse de sécurité
tox -e py312        # pytest — une seule version Python
tox -e coverage     # pytest + rapport de couverture (install éditable)
```

Tous les environnements doivent passer avant d'ouvrir une merge request.

---

## Tests d'intégration

Les tests d'intégration s'exécutent contre une instance PostgreSQL réelle avec
l'extension `ltree`. Ils ne tournent qu'en local jusqu'à la v1.0.0 (DD-011).

### Configuration PostgreSQL

Se connecter en tant que superutilisateur PostgreSQL et exécuter :

```sql
CREATE USER clade_dev WITH PASSWORD 'votre_mot_de_passe';
CREATE DATABASE clade_test OWNER clade_dev;
\c clade_test
CREATE EXTENSION IF NOT EXISTS ltree;
GRANT ALL PRIVILEGES ON DATABASE clade_test TO clade_dev;
```

Django crée la base de test en clonant `template1`. L'extension `ltree` doit
donc être activée sur `template1` également :

```sql
\c template1
CREATE EXTENSION IF NOT EXISTS ltree;
```

Cette étape requiert les droits superutilisateur et n'est à effectuer qu'une
seule fois par installation PostgreSQL.

Ajouter les lignes suivantes dans `pg_hba.conf` :

```
local  clade_test  clade_dev              password
host   clade_test  clade_dev  127.0.0.1/32  scram-sha-256
```

Recharger ensuite PostgreSQL :

```bash
sudo systemctl reload postgresql
```

### Fichier de configuration local

Créer le fichier `tests/settings_integration_local.py` avec le contenu suivant,
puis remplacer `"votre_mot_de_passe"` par votre mot de passe local :

```python
# =============================================================================
# tests/settings_integration_local.py — Credentials locaux pour les tests d'intégration.
#
# CE FICHIER EST DANS .gitignore — ne jamais le commiter.
# =============================================================================

from tests.settings_integration import *  # noqa: F401, F403

DATABASES["default"]["PASSWORD"] = "votre_mot_de_passe"  # noqa: F405
```

Ce fichier est dans `.gitignore` — ne jamais le commiter.

### Lancer les tests d'intégration

**Local** — utilise `settings_integration_local.py` (credentials dans le fichier) :

```bash
tox -e integration
```

**CI** — utilise `settings_integration.py` (mot de passe via la variable `CLADE_DB_PASSWORD`) :

```bash
CLADE_DB_PASSWORD=votre_mot_de_passe tox -e integration-ci
```

L'environnement `integration-ci` est utilisé par le pipeline schedulé GitLab
à partir de la v1.0.0 (DD-011), avec `CLADE_DB_PASSWORD` déclarée comme variable
masquée dans les paramètres du dépôt.

---

## Nommage des branches

Suivre la stratégie de branches du projet :

```
feature/description-courte  →  update/x.y.z  →  staging  →  main
```

Exemples de noms de branches :
- `feature/lookups-ltree`
- `feature/cas-limite-fratrie`
- `feature/guide-contribution`

---

## Messages de commit

Suivre le format [Conventional Commits](https://www.conventionalcommits.org/fr/) :

```
type(scope): description courte

Corps optionnel expliquant le pourquoi, pas le quoi.

Refs: #42
```

Types : `feat`, `fix`, `docs`, `chore`, `ci`, `test`, `refactor`, `perf`, `style`.

---

## Ouvrir une merge request

1. Créer une branche `feature/*` depuis `update/x.y.z`
2. Apporter vos modifications — garder un périmètre ciblé
3. Vérifier que `tox -e pre-push` passe
4. Ouvrir une merge request ciblant `update/x.y.z` sur GitLab avec :
   - Un titre clair suivant la convention de commit
   - Une description expliquant la motivation et l'approche
   - Une référence à l'issue concernée (`Closes #xx`)

---

## Décisions de conception

Les choix architecturaux significatifs sont documentés dans les
[issues DD sur GitLab](https://gitlab.com/open-works/clade/-/issues?label_name=type%3A+decision)
sous forme de fiches numérotées `DD-xxx`.
Si votre contribution implique un choix architectural, ouvrez d'abord une issue
`type: decision` et référencez-la dans votre merge request.

---

## Code de conduite

Tous les contributeurs sont tenus de respecter le
[Code de Conduite](CODE_DE_CONDUITE.md).
