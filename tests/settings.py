# Minimal Django settings for the test suite.
# Not for production use.
#
# Refs: DD-006 (test strategy), DD-009 (toolchain), DD-011 (test environments)
#   https://gitlab.com/open-works/clade/-/issues/6
#   https://gitlab.com/open-works/clade/-/issues/9
#   https://gitlab.com/open-works/clade/-/issues/32

SECRET_KEY = "django-insecure-test-key-not-for-production"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "clade",
    "tests",  # concrete test models (SimpleNode, AdoptNode)
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
