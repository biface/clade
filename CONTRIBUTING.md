# Contributing to Clade

Thank you for your interest in contributing. This document explains how to set up
the development environment and how to submit changes.

---

## Prerequisites

- Python 3.10 or later
- [uv](https://github.com/astral-sh/uv) for virtual environment management
- [tox](https://tox.wiki/) + [tox-uv](https://github.com/tox-dev/tox-uv)
- PyCharm is the recommended IDE, but any editor works

For integration tests only:

- A running PostgreSQL instance (≥ 14) with the `ltree` extension enabled
- A dedicated database and user (see [Integration tests](#integration-tests) below)

---

## Setting up the environment

```bash
git clone git@gitlab.com:open-works/clade.git
cd clade
uv venv
uv sync --extra dev
```

---

## Running the checks locally

All quality checks are orchestrated by tox:

```bash
tox -e pre-push     # full chain: format + quality + tests + coverage
tox -e flake8       # flake8 — lint
tox -e black-check  # black — format check
tox -e isort-check  # isort — import order check
tox -e basedpyright # basedpyright — type checking
tox -e bandit       # bandit — security analysis
tox -e py312        # pytest — single Python version
tox -e coverage     # pytest + coverage report (editable install)
```

All environments must pass before opening a merge request.

---

## Integration tests

Integration tests run against a real PostgreSQL instance with the `ltree`
extension. They are run locally only until v1.0.0 (DD-011).

### PostgreSQL setup

Connect as the PostgreSQL superuser and run:

```sql
CREATE USER clade_dev WITH PASSWORD 'your_password';
CREATE DATABASE clade_test OWNER clade_dev;
\c clade_test
CREATE EXTENSION IF NOT EXISTS ltree;
GRANT ALL PRIVILEGES ON DATABASE clade_test TO clade_dev;
```

Django creates the test database by cloning `template1`. The `ltree` extension
must therefore also be enabled on `template1`:

```sql
\c template1
CREATE EXTENSION IF NOT EXISTS ltree;
```

This step requires superuser privileges and is a one-time operation per
PostgreSQL installation.

Add the following lines to `pg_hba.conf`:

```
local  clade_test  clade_dev              password
host   clade_test  clade_dev  127.0.0.1/32  scram-sha-256
```

Then reload PostgreSQL:

```bash
sudo systemctl reload postgresql
```

### Local settings file

Create `tests/settings_integration_local.py` with the following content,
then replace `"your_password"` with your local password:

```python
# =============================================================================
# tests/settings_integration_local.py — Local credentials for integration tests.
#
# THIS FILE IS GITIGNORED — never commit it.
# =============================================================================

from tests.settings_integration import *  # noqa: F401, F403

DATABASES["default"]["PASSWORD"] = "your_password"  # noqa: F405
```

This file is gitignored — never commit it.

### Running integration tests

**Local** — uses `settings_integration_local.py` (credentials in the file):

```bash
tox -e integration
```

**CI** — uses `settings_integration.py` (password via `CLADE_DB_PASSWORD` env var):

```bash
CLADE_DB_PASSWORD=your_password tox -e integration-ci
```

The `integration-ci` environment is used by the GitLab scheduled pipeline
from v1.0.0 (DD-011), with `CLADE_DB_PASSWORD` declared as a masked variable
in the repository settings.

---

## Branch naming

Follow the project branching strategy:

```
feature/short-description  →  update/x.y.z  →  staging  →  main
```

Branch name examples:
- `feature/ltree-lookups`
- `feature/sibling-edge-case`
- `feature/contributing-guide`

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

1. Create a `feature/*` branch from `update/x.y.z`
2. Make your changes — keep the scope focused
3. Ensure `tox -e pre-push` passes
4. Open a merge request targeting `update/x.y.z` on GitLab with:
   - A clear title following the commit convention
   - A description explaining the motivation and approach
   - A reference to the related issue (`Closes #xx`)

---

## Design decisions

Significant architectural choices are documented in the
[DD issues on GitLab](https://gitlab.com/open-works/clade/-/issues?label_name=type%3A+decision)
as numbered `DD-xxx` records.
If your contribution involves an architectural choice, open a `type: decision`
issue first and reference it in your merge request.

---

## Code of conduct

All contributors are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
