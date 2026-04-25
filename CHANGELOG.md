# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.0.5] — 2026-05-31

### Added
- Repository structure and standard project files
- GitLab labels, milestones, and issue/MR templates
- CI pipeline skeleton (lint, type, security, test)
- `pyproject.toml` with full toolchain configuration (Ruff, Pyright, Bandit, tox, uv)
- Design decisions DD-001 to DD-010 documented as [GitLab issues](https://gitlab.com/open-works/clade/-/issues?label_name=type%3A+decision)
- DD-010: progressive release strategy (manual → semi-auto → fully automated)
- Package distributed as `django-clade` on PyPI; Django module name is `clade`

---

[Unreleased]: https://gitlab.com/open-works/clade/-/compare/v0.0.5...HEAD
[0.0.5]: https://gitlab.com/open-works/clade/-/releases/v0.0.5

