# =============================================================================
# docs/source/conf.py — Sphinx configuration.
#
# #79: project metadata, Furo theme, MyST-Parser, logo (scaffold).
# #80: Django app registry wired for autodoc. Reuses tests.settings — no
# bespoke fourth settings module alongside tests.settings /
# tests.settings_integration / tests.settings_integration_local (DD-017).
# Repo root and src/ added to sys.path so `tests` and `clade` are importable
# from docs/source/. Three levels up from this file: source -> docs -> repo
# root (docs/source split introduced after #79's initial scaffold).
#
# Refs: DD-017 (#78), #79, #80
# =============================================================================

import os
import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django  # noqa: E402  (must follow sys.path/env setup above)

django.setup()

project = "Clade"
copyright = "2026, biface"
author = "biface"

# Read from the installed package's metadata (pyproject.toml [project].version)
# rather than duplicating it here — tox installs django-clade into every
# environment, docs included (.tox-config/requirements/docs.txt), so this
# always reflects the version actually being built, RC or final, with a
# single source of truth. `release` is the full string (e.g. "0.6.0rc1"),
# `version` the short X.Y form Sphinx/Furo use for the sidebar, per Sphinx
# convention.
release = _pkg_version("django-clade")
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_logo = "_static/images/logo.svg"

myst_enable_extensions = [
    "colon_fence",
]

intersphinx_mapping = {
    "django": ("https://docs.djangoproject.com/en/5.2/", None),
}
