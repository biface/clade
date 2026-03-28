# Security Policy

## Supported versions

| Version                  | Supported          |
|--------------------------|--------------------|
| `0.x.y` (pre-release)    | Current minor only |
| `1.x.y` (stable, future) | Latest patch       |

## Static analysis

The codebase is analysed by [Bandit](https://bandit.readthedocs.io/) on every
CI run as part of the quality pipeline. Known findings are reviewed and tracked
as issues with the `type: security` label.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report vulnerabilities privately to the maintainer:

- Email: address available in `pyproject.toml` (`[project.authors]`) or on the
  maintainer's GitLab profile (`gitlab.com/open-works`)
- GitLab confidential issue: use **New issue → Confidential** in the repository

### What to include

- A description of the vulnerability and its potential impact
- Steps to reproduce or a minimal proof-of-concept
- The affected version(s)
- Any suggested fix, if you have one

### Response

This project is maintained on a best-effort basis. There is no guaranteed
response time. Reports will be reviewed and addressed as bandwidth allows.

Public disclosure will be coordinated with the reporter once a fix is available.
