# =============================================================================
# tests/settings_integration_mariadb.py — Django settings for MariaDB
# integration tests. CI ONLY.
#
# This file is committed to the repository and is only ever used by the
# GitLab job ``integrate:mariadb`` (tox environment ``integration-mariadb-ci``).
# There is deliberately no ``_local`` counterpart and no local tox
# environment: MariaDB is verified in CI, not on contributors' machines
# (DD-019). For the PostgreSQL equivalent, see ``settings_integration.py``.
#
# The same integration modules run here as on PostgreSQL
# (``pytest -m integration``); the checks that assert PostgreSQL-specific
# facts (``ltree``) are skipped on this backend.
#
# Configure via environment variables (set by the CI job):
#
#   CLADE_DB_NAME      database name     (default: clade_test)
#   CLADE_DB_USER      database user     (default: root — Django must be able
#                                         to create and drop test_clade_test)
#   CLADE_DB_PASSWORD  user password     (default: empty)
#   CLADE_DB_HOST      server host       (default: 127.0.0.1 — TCP, not socket)
#   CLADE_DB_PORT      server port       (default: 3306)
#
# Character set and collation
# ---------------------------
# The test database is created with an explicit utf8mb4 charset, so the run
# does not depend on the server's default charset. The collation is left at
# the server default on purpose: clade sets no ``db_collation`` anywhere
# (DD-019), so the suite should see what a typical deployment sees. The
# resulting case-insensitive matching on ``Affinity.channel``/``value`` is a
# documented limitation (concepts/affinity.md), not something these tests
# work around.
#
# Refs: DD-003 (#3), DD-011 (#32), DD-019 (#100)
# =============================================================================

import os

SECRET_KEY = "django-insecure-integration-test-key-not-for-production"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("CLADE_DB_NAME", "clade_test"),
        "USER": os.environ.get("CLADE_DB_USER", "root"),
        "PASSWORD": os.environ.get("CLADE_DB_PASSWORD", ""),
        "HOST": os.environ.get("CLADE_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("CLADE_DB_PORT", "3306"),
        "TEST": {
            "NAME": "test_clade_test",
            "CHARSET": "utf8mb4",
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
