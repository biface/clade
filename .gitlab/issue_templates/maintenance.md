# 🔧 Maintenance

## Task type

<!-- Remove the lines that do not apply, then update the label below -->

- **chore** — dependencies, housekeeping, configuration
- **docs** — docstrings, README, guides, examples
- **test** — adding or fixing tests, coverage
- **refactor** — restructuring without behaviour change
- **ci** — pipeline, tox, GitLab CI
- **perf** — performance optimisation
- **deprecation** — mark obsolete code with deprecation warnings

---

## Description

<!-- What needs to be done, and why now? -->

---

## Completion criteria

- [ ] `tox -e lint,type,security` exits 0
- [ ] `pytest` passes
- [ ] Coverage ≥ 80%
- [ ] `CHANGELOG.md` updated if necessary

---

## Urgency (optional)

<!-- Why now rather than later?
     E.g.: CVE, blocking technical debt, prerequisite for a feature. -->

---

## Dependency update detail (optional)

<!-- Fill in only for a dependency-update chore -->

| Package | Before | After | Breaking? |
|---|---|---|---|
|  |  |  |  |

---

## Affected scope

- [ ] `api` — public interface
- [ ] `docs` — docstrings, guides
- [ ] `tests` — pytest, coverage
- [ ] `ci` — pipeline

---

/label ~"status: triage"
