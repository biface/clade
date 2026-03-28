# Contributing to Hierarchy

Thank you for your interest in contributing. This document explains how to set up
the development environment and how to submit changes.

---

## Prerequisites

- Python 3.10 or later
- [uv](https://github.com/astral-sh/uv) for virtual environment management
- [tox](https://tox.wiki/) + [tox-uv](https://github.com/tox-dev/tox-uv)
- A running PostgreSQL instance (for integration tests)
- PyCharm is the recommended IDE, but any editor works

---

## Setting up the environment

```bash
git clone git@gitlab.com:open-works/hierarchy.git
cd hierarchy
uv venv
uv pip install -e ".[dev]"
```

---

## Running the checks locally

All quality checks are orchestrated by tox:

```bash
tox              # run all environments
tox -e lint      # Ruff — lint + format check
tox -e type      # Pyright — type checking
tox -e security  # Bandit — security analysis
tox -e test      # pytest + coverage (default: SQLite backend)
```

All environments must pass before opening a merge request.

---

## Branch naming

```
type/short-description
```

Examples:
- `feat/node-ancestor-query`
- `fix/sibling-edge-case`
- `chore/update-ruff`
- `docs/contributing-guide`

---

## Commit messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): short description

Optional body explaining the why, not the what.

Refs: #42
```

Types: `feat`, `fix`, `docs`, `chore`, `ci`, `test`, `refactor`, `perf`, `style`.

---

## Opening a merge request

1. Fork the repository or create a branch from `main`
2. Make your changes — keep the scope focused
3. Ensure all tox environments pass
4. Open a merge request on GitLab with:
   - A clear title following the commit convention
   - A description explaining the motivation and approach
   - A reference to the related issue (`Closes #xx`)

---

## Design decisions

Significant architectural choices are documented in
the [DD issues on GitLab](https://gitlab.com/open-works/hierarchy/-/issues?label_name=type%3A+decision) as numbered `DD-xxx` records.
If your contribution involves an architectural choice, open a `type: decision`
issue first and reference it in your merge request.

---

## Code of conduct

All contributors are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
