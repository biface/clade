# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.4.0] — 2026-07-07

### Added
- `NLevel` — internal `Func` expression wrapping the PostgreSQL `nlevel(path)`
  function; used by `cousins_of()` for exact-depth filtering (DD-016)
- `NodeQuerySet.piblings_of()` / `node.piblings()` — siblings of a node's
  parent; pure composition of `siblings_of()`, no new SQL (DD-016)
- `NodeQuerySet.niblings_of()` / `node.niblings()` — children of a node's
  siblings; pure composition of `siblings_of()`, no new SQL (DD-016)
- `NodeQuerySet.cousins_of(node, degree=2)` / `node.cousins(degree=2)` —
  symmetric-degree cousin queries (DD-016); PostgreSQL dispatch via the
  `descendant_of` ltree lookup and `NLevel`, fallback via `__startswith` and
  `Length`/`Replace` dot-counting
- `NodeManager` proxies for the three new methods
- `kinship_tree` / `pg_kinship_tree` fixtures — additive extended-tree
  fixtures dedicated to the three new relationships (kept separate from
  `tree` / `pg_tree` to avoid breaking existing leaf-node assertions)
- 18 SQLite unit tests, 5 PostgreSQL dispatch tests, and 14 PostgreSQL
  integration parity tests for extended kinship
- `README.md` / `README.fr.md` usage examples for `piblings()`, `niblings()`,
  `cousins()`

---

## [0.3.0] — 2026-06-13

### Added
- `LtreeField` — custom `CharField` subclass; returns `ltree` on PostgreSQL,
  `varchar(N)` on all other backends; registers `ancestor_of` (`@>`) and
  `descendant_of` (`<@`) lookups (DD-015)
- `ConditionalAlterField` — custom migration operation; executes
  `ALTER COLUMN … TYPE ltree` on PostgreSQL only, no-op on other backends (DD-015)
- `NodeQuerySet` PostgreSQL dispatch — `ancestors_of` and `descendants_of` use
  native ltree operators on PostgreSQL, `__in` / `__startswith` fallback elsewhere
- Integration test suite — 26 parity tests SQLite vs PostgreSQL
  (`test_integration.py`, `test_hierarchy_pg_dispatch.py`)
- `tests/settings_integration.py` — dedicated Django settings for integration tests,
  credentials injected via `CLADE_DB_*` environment variables
- `tox -e integration` and `tox -e integration-ci` environments (DD-011)
- CI `integration-ci` job — PostgreSQL 16 service, ltree on `template1`,
  triggered on version tags and scheduled pipelines

### Changed
- `CladeNode.path` field type updated from `CharField` to `LtreeField` (DD-015)
- `pyproject.toml`: `passenv` added to `integration-ci` for `CLADE_DB_*` variables
- `.gitlab-ci.yml`: `POSTGRES_HOST_AUTH_METHOD` set to `trust`; ltree enabled on
  `template1` before Django creates the test database

### Fixed
- ltree operators `@>` / `<@` are inclusive — `.exclude(pk=node.pk)` added to
  `ancestors_of` and `descendants_of` PostgreSQL branches

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

[Unreleased]: https://gitlab.com/open-works/clade/-/compare/v0.4.0...HEAD
[0.4.0]: https://gitlab.com/open-works/clade/-/releases/v0.4.0
[0.3.0]: https://gitlab.com/open-works/clade/-/releases/v0.3.0
[0.2.0]: https://gitlab.com/open-works/clade/-/releases/v0.2.0
[0.1.0]: https://gitlab.com/open-works/clade/-/releases/v0.1.0
[0.0.5]: https://gitlab.com/open-works/clade/-/releases/v0.0.5
