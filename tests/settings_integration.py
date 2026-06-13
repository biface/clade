# =============================================================================
# tests/settings_integration.py — Django settings for integration tests.
#
# This file is committed to the repository and serves as:
#   - The CI configuration (credentials injected via environment variables)
#   - The template for local development (see CONTRIBUTING.md)
#
# For local development, copy this file to settings_integration_local.py
# and set your local credentials there. That file is gitignored.
#
# Requires a PostgreSQL instance with:
#   - A dedicated database (default: clade_test) owned by a dedicated user
#   - Password authentication configured in pg_hba.conf, e.g.:
#       local  clade_test  clade_dev              password
#       host   clade_test  clade_dev  127.0.0.1/32  scram-sha-256
#   - The ltree extension enabled on that database:
#       CREATE EXTENSION IF NOT EXISTS ltree;
#
# Configure via environment variables:
#
#   CLADE_DB_NAME      database name     (default: clade_test)
#   CLADE_DB_USER      database user     (default: clade_dev)
#   CLADE_DB_PASSWORD  user password     (default: empty — set locally)
#   CLADE_DB_HOST      server host       (default: localhost)
#   CLADE_DB_PORT      server port       (default: 5432)
#
# Run with:
#   tox -e integration
#
# Or with local overrides:
#   DJANGO_SETTINGS_MODULE=tests.settings_integration_local tox -e integration
#
# Refs: DD-006 (#6), DD-011 (#32), DD-015
# =============================================================================

import os

SECRET_KEY = "django-insecure-integration-test-key-not-for-production"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("CLADE_DB_NAME", "clade_test"),
        "USER": os.environ.get("CLADE_DB_USER", "clade_dev"),
        "PASSWORD": os.environ.get("CLADE_DB_PASSWORD", ""),
        "HOST": os.environ.get("CLADE_DB_HOST", "localhost"),
        "PORT": os.environ.get("CLADE_DB_PORT", "5432"),
        "TEST": {
            "NAME": "test_clade_test",
        },
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "clade",
    "tests",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
