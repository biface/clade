# 🐛 Bug Report

## Summary

<!-- One sentence: what happens vs what should happen. -->

**Observed:** 
**Expected:** 

---

## Reproduction steps

<!-- Minimal Python code reproducing the issue (MCVE). A failing pytest is ideal. -->

```python

```

---

## Environment

| Field | Value |
|---|---|
| **Package version** | <!-- output of: pip show hierarchy \| grep Version --> |
| **Python version** | <!-- output of: python --version --> |
| **Django version** | <!-- output of: python -m django --version --> |
| **OS** | <!-- Linux / macOS / Windows --> |

---

## Affected scope

<!-- Check all that apply -->

- [ ] `api` — public interface
- [ ] `docs` — docstrings, examples
- [ ] `tests` — pytest, coverage
- [ ] `ci` — pipeline

---

## Severity

<!-- Remove the lines that do not apply -->

- **high** — unhandled exception, data corruption, public regression
- **medium** — incorrect behaviour, workaround available
- **low** — cosmetic, imprecise error message

---

## Additional context

<!-- Full traceback, logs, pip freeze output, etc. -->

---

/label ~"type: bug" ~"status: triage" ~"priority: high"
