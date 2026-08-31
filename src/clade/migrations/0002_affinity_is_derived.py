# =============================================================================
# clade/migrations/0002_affinity_is_derived.py — Add Affinity.is_derived
# (DD-018, v0.6.0, #89).
#
# Distinguishes derived pairs (declared-rule graph closure, clade/closure.py)
# from direct pairs (v0.5.0 signal handlers, DD-005). Existing rows default
# to is_derived=False — every v0.5.0 row is direct by construction.
#
# Identical DDL on every backend: a plain BooleanField, no conditional
# DDL involved (DD-015's pattern does not apply here — see 0001_affinity.py).
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clade", "0001_affinity"),
    ]

    operations = [
        migrations.AddField(
            model_name="affinity",
            name="is_derived",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "False for a direct pair materialised by the v0.5.0 "
                    "signal handlers (DD-005). True for a pair produced by "
                    "the declared-rule graph closure (DD-018, v0.6.0) — "
                    "see clade/closure.py."
                ),
            ),
        ),
    ]
