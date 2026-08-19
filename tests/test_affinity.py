# =============================================================================
# tests/test_affinity.py — Affinity storage, signal maintenance, and checks
# (DD-005, v0.5.0).
#
# Fixture models: tests.models.AffinityDepartment / AffinityDepartmentAlt
# (sources) and tests.models.AffinityProject (passive target) — see
# tests/models.py for the declared AffinityRule set.
#
# Refs: DD-004 (#4), DD-005 (#5), clade.E001, clade.E002
# =============================================================================

import pytest
from django.test.utils import isolate_apps

from clade.affinity import (
    Affinity,
    HeterogeneousAffinityError,
    affinities_of,
    affinities_of_grouped,
)
from clade.checks import check_affinity_channel_uniqueness, check_affinity_field_types
from tests.models import AffinityDepartment, AffinityDepartmentAlt, AffinityProject


def _pairs(channel=None):
    """Return {(side_a, side_b)} for readable assertions, optionally
    filtered to one channel."""
    qs = Affinity.objects.all()
    if channel is not None:
        qs = qs.filter(channel=channel)
    return {(a.side_a, a.side_b) for a in qs}


@pytest.mark.django_db
class TestAffinitySourceTrigger:
    """Saving the declaring (source) model recalculates its rows."""

    def test_source_save_creates_matching_rows(self):
        p1 = AffinityProject.objects.create(
            title="P1", cost_center="paris", lead="alice"
        )
        p2 = AffinityProject.objects.create(title="P2", cost_center="paris", lead="bob")
        d1 = AffinityDepartment.objects.create(
            name="D1", region="paris", manager="alice"
        )

        assert _pairs("geo") == {(d1, p1), (d1, p2)}
        assert _pairs("management") == {(d1, p1)}

    def test_source_save_with_no_match_creates_nothing(self):
        AffinityProject.objects.create(title="P1", cost_center="lyon")
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")

        assert not Affinity.objects.filter(object_id_a=d1.pk).exists()

    def test_null_local_field_creates_nothing(self):
        """A None value never matches — not even another None (DD-005)."""
        AffinityProject.objects.create(title="P1", cost_center=None)
        d1 = AffinityDepartment.objects.create(name="D1", region=None)

        assert not Affinity.objects.filter(object_id_a=d1.pk, channel="geo").exists()

    def test_source_value_change_replaces_stale_rows(self):
        p_paris = AffinityProject.objects.create(title="P-paris", cost_center="paris")
        p_lyon = AffinityProject.objects.create(title="P-lyon", cost_center="lyon")
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        assert _pairs("geo") == {(d1, p_paris)}

        d1.region = "lyon"
        d1.save()

        assert _pairs("geo") == {(d1, p_lyon)}


@pytest.mark.django_db
class TestAffinityTargetTrigger:
    """Saving a passive target (never itself declaring rules) also
    recalculates — the bidirectional-registry gap DD-005 closed."""

    def test_target_save_after_source_creates_row(self):
        """Reverse-index trigger: no AffinityDepartment save involved."""
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        assert not Affinity.objects.filter(channel="geo").exists()

        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")

        assert _pairs("geo") == {(d1, p1)}

    def test_target_value_change_replaces_stale_rows(self):
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        assert _pairs("geo") == {(d1, p1)}

        p1.cost_center = "lyon"
        p1.save()

        assert not Affinity.objects.filter(channel="geo").exists()

    def test_target_null_value_creates_nothing(self):
        AffinityDepartment.objects.create(name="D1", region="paris")
        p1 = AffinityProject.objects.create(title="P1", cost_center=None)

        assert not Affinity.objects.filter(object_id_b=p1.pk, channel="geo").exists()


@pytest.mark.django_db
class TestAffinityChannelCollision:
    """Two different source models reusing the same channel name must not
    clobber each other's rows (content_type_a scoping, not channel-only)."""

    def test_cross_source_same_channel_no_wipeout(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        d2 = AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

        assert _pairs("geo") == {(d1, p1), (d2, p1)}

        # Re-saving p1 (target-side resync for BOTH rules) must not drop
        # either source's row.
        p1.save()

        assert _pairs("geo") == {(d1, p1), (d2, p1)}


@pytest.mark.django_db
class TestAffinityDeletion:
    """post_delete purges every row referencing the deleted instance,
    on either side, regardless of channel."""

    def test_deleting_source_purges_its_rows(self):
        p1 = AffinityProject.objects.create(
            title="P1", cost_center="paris", lead="alice"
        )
        d1 = AffinityDepartment.objects.create(
            name="D1", region="paris", manager="alice"
        )
        assert Affinity.objects.count() == 2

        d1.delete()

        assert Affinity.objects.count() == 0

    def test_deleting_target_purges_referencing_rows(self):
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        assert Affinity.objects.count() == 1

        p1.delete()

        assert Affinity.objects.count() == 0

    def test_deleting_one_of_several_targets_keeps_the_others(self):
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        p2 = AffinityProject.objects.create(title="P2", cost_center="paris")
        assert _pairs("geo") == {(d1, p1), (d1, p2)}

        p1.delete()

        assert _pairs("geo") == {(d1, p2)}


@pytest.mark.django_db
class TestAffinityChecks:
    """clade.E001 / clade.E002 against the real test-app registry."""

    def test_no_errors_for_valid_registry(self):
        assert check_affinity_channel_uniqueness(app_configs=None) == []
        assert check_affinity_field_types(app_configs=None) == []

    @isolate_apps("tests")
    def test_duplicate_channel_is_reported(self):
        from django.db import models as dj_models

        from clade.affinity import AffinityRule
        from clade.models import CladeNode

        class DupChannelNode(CladeNode):
            region = dj_models.CharField(max_length=64, null=True)
            manager = dj_models.CharField(max_length=64, null=True)

            class Meta(CladeNode.Meta):
                affinity_rules = [
                    AffinityRule(
                        "region",
                        to="tests.AffinityProject",
                        target_field="cost_center",
                        channel="geo",
                    ),
                    AffinityRule(
                        "manager",
                        to="tests.AffinityProject",
                        target_field="lead",
                        channel="geo",  # duplicate within this model
                    ),
                ]

        errors = check_affinity_channel_uniqueness(app_configs=None)
        ids = {e.id for e in errors}
        assert "clade.E001" in ids
        assert any(e.obj is DupChannelNode for e in errors)

    @isolate_apps("tests")
    def test_disallowed_field_type_is_reported(self):
        from django.db import models as dj_models

        from clade.affinity import AffinityRule
        from clade.models import CladeNode

        class FileFieldNode(CladeNode):
            logo = dj_models.FileField(null=True)

            class Meta(CladeNode.Meta):
                affinity_rules = [
                    AffinityRule(
                        "logo",
                        to="tests.AffinityProject",
                        target_field="cost_center",
                        channel="geo",
                    ),
                ]

        errors = check_affinity_field_types(app_configs=None)
        ids = {e.id for e in errors}
        assert "clade.E002" in ids
        assert any(e.obj is FileFieldNode for e in errors)


@pytest.mark.django_db
class TestAffinitiesOfHomogeneous:
    """affinities_of() — single-model result, the common case."""

    def test_source_side_returns_typed_queryset_of_target_model(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        p2 = AffinityProject.objects.create(title="P2", cost_center="paris")
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")

        result = affinities_of(d1, channel="geo")

        assert result.model is AffinityProject
        assert set(result) == {p1, p2}

    def test_target_side_returns_typed_queryset_of_source_model(self):
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")

        result = affinities_of(p1, channel="geo")

        assert result.model is AffinityDepartment
        assert set(result) == {d1}

    def test_no_channel_across_two_rules_same_target_is_homogeneous(self):
        """D1 matches P1 via both "geo" and "management" — both rules
        target AffinityProject, so the unfiltered result is still a
        single-model QuerySet (partner *instances* may repeat via
        different channels, but the model is the same)."""
        p1 = AffinityProject.objects.create(
            title="P1", cost_center="paris", lead="alice"
        )
        d1 = AffinityDepartment.objects.create(
            name="D1", region="paris", manager="alice"
        )

        result = affinities_of(d1)

        assert result.model is AffinityProject
        assert set(result) == {p1}

    def test_no_matching_rows_returns_empty_typed_queryset(self):
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")

        result = affinities_of(d1, channel="geo")

        assert result.model is AffinityProject
        assert not result.exists()

    def test_no_channel_no_matches_falls_back_to_empty_affinity_queryset(self):
        """No rows, no channel to resolve a rule from — undeterminable
        partner type, documented fallback to an empty Affinity qs."""
        d1 = AffinityDepartment.objects.create(name="D1", region=None, manager=None)

        result = affinities_of(d1)

        assert result.model is Affinity
        assert not result.exists()

    def test_instance_method_delegates(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")

        assert set(d1.affinities(channel="geo")) == set(
            affinities_of(d1, channel="geo")
        )


@pytest.mark.django_db
class TestAffinitiesOfHeterogeneous:
    """affinities_of() raises when partners span more than one model;
    affinities_of_grouped() never raises."""

    def test_raises_when_two_source_models_share_channel(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        AffinityDepartment.objects.create(name="D1", region="paris")
        AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

        with pytest.raises(HeterogeneousAffinityError):
            affinities_of(p1, channel="geo")

    def test_grouped_never_raises_and_splits_by_model(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        d1 = AffinityDepartment.objects.create(name="D1", region="paris")
        d2 = AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

        result = affinities_of_grouped(p1, channel="geo")

        assert set(result.keys()) == {AffinityDepartment, AffinityDepartmentAlt}
        assert set(result[AffinityDepartment]) == {d1}
        assert set(result[AffinityDepartmentAlt]) == {d2}

    def test_grouped_empty_dict_when_no_matches(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="lyon")

        result = affinities_of_grouped(p1, channel="geo")

        assert result == {}

    def test_instance_method_grouped_delegates(self):
        p1 = AffinityProject.objects.create(title="P1", cost_center="paris")
        AffinityDepartment.objects.create(name="D1", region="paris")
        AffinityDepartmentAlt.objects.create(name="D2", zone="paris")

        manager_result = affinities_of_grouped(p1, channel="geo")
        instance_result = p1.affinities_grouped(channel="geo")

        assert set(manager_result.keys()) == set(instance_result.keys())
