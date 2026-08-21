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
