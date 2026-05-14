# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0] — 2026-05-14

### Added
- `CladeNode` abstract base class with `parent` FK and `path` field (DD-012, DD-013)
- `ADOPT` custom `on_delete` callable — re-parents children to grandparent on
  deletion, works with both `instance.delete()` and `QuerySet.delete()` (DD-014)
- Path maintenance via `post_save` and `post_delete` signals, SQLite backend (DD-013)
- `NodeQuerySet`: `ancestors_of`, `descendants_of`, `siblings_of`, `root_of`
- `CladeNode` instance methods: `ancestors()`, `descendants()`, `siblings()`,
  `root`, `is_root`, `is_leaf`
- Test infrastructure: `SimpleNode`, `AdoptNode`, reference tree fixture, `conftest.py`
- Full test suite: path maintenance, hierarchy queries, ADOPT deletion

### Changed
- CI: `--no-migrations` for standard test runs; `migrations` job on MR→staging
- CI: branching strategy `feature/* → update/x.y.z → staging → main`
- CI: remove `|| [ $? -eq 5 ]` workaround — real tests now collected
- Toolchain: `flake8` + `black` + `isort` + `basedpyright` (aligned with ndict-tools)
- Toolchain: `*.django.txt` naming convention for Django-specific requirements
- Toolchain: `typeCheckingMode` standard (django-stubs compatibility)

### Fixed
- `ADOPT` refactored as class-based callable (basedpyright `reportFunctionMemberAccess`)

---

## [0.1.0] — 2026-04-25

### Added
- Django module scaffolding: `src/clade/` structure (`__init__.py`, `apps.py`,
  `models.py`, `migrations/`)
- `tests/settings.py`: minimal pytest-django settings, SQLite in-memory database
- `pyproject.toml`: packaging metadata completed for PyPI distribution
  (classifiers, keywords, project URLs)
- CI pipeline green on all quality and test jobs
- codecov.io connected with repository token

---

## [0.0.5] — 2026-04-24

### Added
- Repository structure and standard project files
- GitLab labels, milestones, and issue/MR templates
- CI pipeline skeleton (lint, type, security, test)
- `pyproject.toml` with full toolchain configuration (Ruff, Pyright, Bandit, tox, uv)
- Design decisions DD-001 to DD-010 documented as [GitLab issues](https://gitlab.com/open-works/clade/-/issues?label_name=type%3A+decision)
- DD-010: progressive release strategy (manual → semi-auto → fully automated)
- Package distributed as `django-clade` on PyPI; Django module name is `clade`

---

[Unreleased]: https://gitlab.com/open-works/clade/-/compare/v0.2.0...HEAD
[0.2.0]: https://gitlab.com/open-works/clade/-/releases/v0.2.0
[0.1.0]: https://gitlab.com/open-works/clade/-/releases/v0.1.0
[0.0.5]: https://gitlab.com/open-works/clade/-/releases/v0.0.5
