# =============================================================================
# docs/conf.py — Sphinx configuration.
#
# Scaffold only (#79): project metadata, Furo theme, MyST-Parser. No
# django.setup() / autodoc wiring here — that's #80, added once this base
# builds cleanly (`tox -e docs`). sphinx.ext.autodoc and sphinx.ext.napoleon
# are intentionally NOT in the extensions list yet; adding them without a
# configured Django app registry would fail as soon as docs/reference/api.md
# gains real autodoc directives (still a placeholder as of #79 — see #81).
#
# Refs: DD-017 (#78), #79, #80
# =============================================================================

project = "Clade"
copyright = "2026, open-works"
author = "biface"

extensions = [
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
