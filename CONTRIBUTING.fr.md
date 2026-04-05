# Contribuer à Clade

Merci de votre intérêt pour le projet. Ce document explique comment configurer
l'environnement de développement et soumettre des modifications.

---

## Prérequis

- Python 3.10 ou supérieur
- [uv](https://github.com/astral-sh/uv) pour la gestion de l'environnement virtuel
- [tox](https://tox.wiki/) + [tox-uv](https://github.com/tox-dev/tox-uv)
- Une instance PostgreSQL accessible (pour les tests d'intégration)
- PyCharm est l'IDE recommandé, mais tout éditeur convient

---

## Mise en place de l'environnement

```bash
git clone git@gitlab.com:open-works/clade.git
cd clade
uv venv
uv pip install -e ".[dev]"
```

---

## Lancer les vérifications en local

Toutes les vérifications qualité sont orchestrées par tox :

```bash
tox              # lancer tous les environnements
tox -e lint      # Ruff — lint et vérification du format
tox -e type      # Pyright — vérification des types
tox -e security  # Bandit — analyse de sécurité
tox -e test      # pytest + couverture (par défaut : backend SQLite)
```

Tous les environnements doivent passer avant d'ouvrir une merge request.

---

## Nommage des branches

```
type/description-courte
```

Exemples :
- `feat/requete-ancetres-noeud`
- `fix/cas-limite-fratrie`
- `chore/mise-a-jour-ruff`
- `docs/guide-contribution`

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

1. Forkez le dépôt ou créez une branche depuis `main`
2. Apportez vos modifications — gardez un périmètre ciblé
3. Vérifiez que tous les environnements tox passent
4. Ouvrez une merge request sur GitLab avec :
   - Un titre clair suivant la convention de commit
   - Une description expliquant la motivation et l'approche
   - Une référence à l'issue concernée (`Closes #xx`)

---

## Décisions de conception

Les choix architecturaux significatifs sont documentés dans
les [issues DD sur GitLab](https://gitlab.com/open-works/clade/-/issues?label_name=type%3A+decision) sous forme de fiches numérotées `DD-xxx`.
Si votre contribution implique un choix architectural, ouvrez d'abord une issue
`type: decision` et référencez-la dans votre merge request.

---

## Code de conduite

Tous les contributeurs sont tenus de respecter le
[Code de Conduite](CODE_DE_CONDUITE.md).
