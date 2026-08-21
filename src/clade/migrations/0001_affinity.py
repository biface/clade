# =============================================================================
# clade/migrations/0001_affinity.py — Initial migration for the Affinity
# model (DD-005, v0.5.0).
#
# The clade app had no concrete models prior to this migration (CladeNode
# is abstract; concrete subclasses live in — and are migrated by — user
# apps). Affinity is the first concrete model owned by clade itself.
#
# Identical DDL on every backend: Affinity uses only ContentType FKs and
# CharFields — no LtreeField/ConditionalAlterField involved (DD-015's
# conditional-DDL pattern does not apply here).
# =============================================================================

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Affinity",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("object_id_a", models.PositiveBigIntegerField()),
                ("object_id_b", models.PositiveBigIntegerField()),
                ("channel", models.CharField(max_length=255)),
                ("value", models.CharField(max_length=255)),
                (
                    "content_type_a",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "content_type_b",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="affinity",
            index=models.Index(
                fields=["content_type_a", "object_id_a", "channel", "value"],
                name="clade_affin_side_a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="affinity",
            index=models.Index(
                fields=["content_type_b", "object_id_b", "channel", "value"],
                name="clade_affin_side_b_idx",
            ),
        ),
    ]
