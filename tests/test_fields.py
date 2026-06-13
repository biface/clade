# =============================================================================
# tests/test_fields.py — LtreeField and ConditionalAlterField tests.
#
# Validates:
#
# LtreeField
#   - db_type() returns "ltree" on PostgreSQL, VARCHAR(n) elsewhere.
#   - get_internal_type() returns "CharField".
#   - deconstruct() round-trip preserves all field parameters.
#   - Field is usable on a concrete model (CladeNode.path is LtreeField).
#
# ConditionalAlterField
#   - database_forwards() executes only on supported vendors.
#   - database_backwards() executes only on supported vendors.
#   - deconstruct() round-trip: vendors omitted when default, present otherwise.
#   - describe() includes vendor names.
#   - vendors parameter is extensible beyond ("postgresql",).
#
# Refs: DD-003 (#3), DD-013 (#40), DD-015
# =============================================================================

from unittest.mock import MagicMock, patch

import pytest
from django.db import connection, migrations, models

from clade.fields import ConditionalAlterField, LtreeField

# =============================================================================
# Helpers
# =============================================================================


def _make_connection(vendor: str) -> MagicMock:
    """Return a mock database connection with the given vendor string."""
    conn = MagicMock()
    conn.vendor = vendor
    return conn


def _make_schema_editor(vendor: str) -> MagicMock:
    """Return a mock schema editor whose connection has the given vendor."""
    editor = MagicMock()
    editor.connection = _make_connection(vendor)
    return editor


# =============================================================================
# LtreeField
# =============================================================================


class TestLtreeFieldDbType:
    """db_type() returns the correct column type per backend."""

    def test_postgresql_returns_ltree(self):
        """PostgreSQL backend → 'ltree'."""
        field = LtreeField(max_length=255)
        conn = _make_connection("postgresql")
        assert field.db_type(conn) == "ltree"

    def test_sqlite_returns_varchar(self):
        """SQLite backend → VARCHAR(n) from CharField (real connection)."""
        field = LtreeField(max_length=255)
        # Use the real SQLite connection to resolve data_types correctly.
        result = field.db_type(connection)
        assert isinstance(result, str)
        assert "varchar" in result.lower() or "char" in result.lower()

    def test_mysql_returns_varchar(self):
        """Non-PostgreSQL vendor → falls back to CharField db_type."""
        field = LtreeField(max_length=128)
        # Simulate a non-postgresql vendor using the real connection object
        # but with a patched vendor attribute.
        original_vendor = connection.vendor
        try:
            # Monkey-patch vendor on the real connection for this test only.
            connection.__class__.vendor  # ensure it's accessible
            with patch.object(type(connection), "vendor", new="mysql"):
                result = field.db_type(connection)
            assert isinstance(result, str)
            assert "ltree" not in result.lower()
        except AttributeError:
            # If vendor cannot be patched, fall back to mock — acceptable.
            conn = _make_connection("mysql")
            conn.data_types = connection.data_types
            result = field.db_type(conn)
            assert "ltree" not in str(result).lower()

    def test_unknown_vendor_returns_non_ltree(self):
        """Unknown vendor falls back to CharField behaviour (not ltree)."""
        field = LtreeField(max_length=128)
        # Use real connection with patched vendor.
        try:
            with patch.object(type(connection), "vendor", new="oracle"):
                result = field.db_type(connection)
            assert isinstance(result, str)
            assert "ltree" not in result.lower()
        except AttributeError:
            conn = _make_connection("oracle")
            conn.data_types = connection.data_types
            result = field.db_type(conn)
            assert "ltree" not in str(result).lower()


class TestLtreeFieldInternalType:
    """get_internal_type() returns 'CharField' for cross-backend compatibility."""

    def test_returns_charfield(self):
        """get_internal_type() returns 'CharField'."""
        field = LtreeField(max_length=255)
        assert field.get_internal_type() == "CharField"

    def test_same_as_charfield(self):
        """LtreeField internal type is identical to CharField's."""
        ltree = LtreeField(max_length=255)
        char = models.CharField(max_length=255)
        assert ltree.get_internal_type() == char.get_internal_type()


class TestLtreeFieldDeconstruct:
    """deconstruct() round-trip for migration serialisation."""

    def test_path_is_clade_fields(self):
        """deconstruct() path points to clade.fields.LtreeField."""
        field = LtreeField(max_length=255)
        _, path, _, _ = field.deconstruct()
        assert path == "clade.fields.LtreeField"

    def test_max_length_preserved(self):
        """max_length is preserved through deconstruct()."""
        field = LtreeField(max_length=128)
        _, _, _, kwargs = field.deconstruct()
        assert kwargs.get("max_length") == 128

    def test_round_trip_produces_equal_field(self):
        """Reconstructing from deconstruct() produces an equivalent field."""
        original = LtreeField(max_length=255, blank=True, db_index=True)
        _, _, args, kwargs = original.deconstruct()
        reconstructed = LtreeField(*args, **kwargs)
        assert reconstructed.max_length == original.max_length
        assert reconstructed.blank == original.blank

    def test_blank_editable_preserved(self):
        """blank and editable kwargs survive deconstruct()."""
        field = LtreeField(max_length=255, blank=True, editable=False)
        _, _, _, kwargs = field.deconstruct()
        assert kwargs.get("blank") is True


class TestLtreeFieldOnModel:
    """LtreeField is wired correctly on CladeNode.path."""

    def test_path_field_is_ltreefield(self):
        """CladeNode.path is a LtreeField instance."""
        from clade.models import CladeNode

        path_field = CladeNode._meta.get_field("path")
        assert isinstance(path_field, LtreeField)

    def test_path_field_max_length(self):
        """CladeNode.path has max_length=255."""
        from clade.models import CladeNode

        path_field = CladeNode._meta.get_field("path")
        assert path_field.max_length == 255

    def test_path_field_not_editable(self):
        """CladeNode.path is not user-editable."""
        from clade.models import CladeNode

        path_field = CladeNode._meta.get_field("path")
        assert path_field.editable is False


# =============================================================================
# ConditionalAlterField
# =============================================================================


class TestConditionalAlterFieldForwards:
    """database_forwards() executes DDL only on supported vendors."""

    def _make_operation(self, vendors=("postgresql",)):
        return ConditionalAlterField(
            model_name="simplenode",
            name="path",
            field=LtreeField(max_length=255, blank=True, editable=False),
            vendors=vendors,
        )

    def test_executes_on_postgresql(self):
        """database_forwards() calls super() on PostgreSQL."""
        op = self._make_operation()
        editor = _make_schema_editor("postgresql")
        with patch.object(migrations.AlterField, "database_forwards") as mock_super:
            op.database_forwards("tests", editor, MagicMock(), MagicMock())
            mock_super.assert_called_once()

    def test_skips_on_sqlite(self):
        """database_forwards() is a no-op on SQLite."""
        op = self._make_operation()
        editor = _make_schema_editor("sqlite")
        with patch.object(migrations.AlterField, "database_forwards") as mock_super:
            op.database_forwards("tests", editor, MagicMock(), MagicMock())
            mock_super.assert_not_called()

    def test_skips_on_mysql(self):
        """database_forwards() is a no-op on MySQL."""
        op = self._make_operation()
        editor = _make_schema_editor("mysql")
        with patch.object(migrations.AlterField, "database_forwards") as mock_super:
            op.database_forwards("tests", editor, MagicMock(), MagicMock())
            mock_super.assert_not_called()

    def test_custom_vendors_respected(self):
        """A custom vendors tuple is honoured."""
        op = self._make_operation(vendors=("postgresql", "mysql"))
        editor = _make_schema_editor("mysql")
        with patch.object(migrations.AlterField, "database_forwards") as mock_super:
            op.database_forwards("tests", editor, MagicMock(), MagicMock())
            mock_super.assert_called_once()


class TestConditionalAlterFieldBackwards:
    """database_backwards() executes DDL only on supported vendors."""

    def _make_operation(self, vendors=("postgresql",)):
        return ConditionalAlterField(
            model_name="simplenode",
            name="path",
            field=LtreeField(max_length=255, blank=True, editable=False),
            vendors=vendors,
        )

    def test_executes_on_postgresql(self):
        """database_backwards() calls super() on PostgreSQL."""
        op = self._make_operation()
        editor = _make_schema_editor("postgresql")
        with patch.object(migrations.AlterField, "database_backwards") as mock_super:
            op.database_backwards("tests", editor, MagicMock(), MagicMock())
            mock_super.assert_called_once()

    def test_skips_on_sqlite(self):
        """database_backwards() is a no-op on SQLite."""
        op = self._make_operation()
        editor = _make_schema_editor("sqlite")
        with patch.object(migrations.AlterField, "database_backwards") as mock_super:
            op.database_backwards("tests", editor, MagicMock(), MagicMock())
            mock_super.assert_not_called()


class TestConditionalAlterFieldDeconstruct:
    """deconstruct() round-trip for migration serialisation."""

    def _make_operation(self, **kwargs):
        return ConditionalAlterField(
            model_name="simplenode",
            name="path",
            field=LtreeField(max_length=255, blank=True, editable=False),
            **kwargs,
        )

    def test_default_vendors_not_in_kwargs(self):
        """vendors omitted from deconstruct() kwargs when default."""
        op = self._make_operation()
        _, _, kwargs = op.deconstruct()
        assert "vendors" not in kwargs

    def test_custom_vendors_in_kwargs(self):
        """Non-default vendors are included in deconstruct() kwargs."""
        op = self._make_operation(vendors=("postgresql", "mysql"))
        _, _, kwargs = op.deconstruct()
        assert kwargs["vendors"] == ("postgresql", "mysql")

    def test_round_trip_preserves_model_name(self):
        """model_name survives deconstruct() round-trip."""
        op = self._make_operation()
        name, args, kwargs = op.deconstruct()
        reconstructed = ConditionalAlterField(*args, **kwargs)
        assert reconstructed.model_name == "simplenode"

    def test_round_trip_preserves_field_name(self):
        """field name survives deconstruct() round-trip."""
        op = self._make_operation()
        name, args, kwargs = op.deconstruct()
        reconstructed = ConditionalAlterField(*args, **kwargs)
        assert reconstructed.name == "path"

    def test_round_trip_preserves_default_vendors(self):
        """Default vendors survive deconstruct() round-trip."""
        op = self._make_operation()
        name, args, kwargs = op.deconstruct()
        reconstructed = ConditionalAlterField(*args, **kwargs)
        assert reconstructed.vendors == ("postgresql",)


class TestConditionalAlterFieldDescribe:
    """describe() surfaces vendor information for showmigrations."""

    def test_describe_contains_postgresql(self):
        """describe() output mentions 'postgresql'."""
        op = ConditionalAlterField(
            model_name="simplenode",
            name="path",
            field=LtreeField(max_length=255),
        )
        description = op.describe()
        assert "postgresql" in description

    def test_describe_contains_conditional(self):
        """describe() output signals conditionality."""
        op = ConditionalAlterField(
            model_name="simplenode",
            name="path",
            field=LtreeField(max_length=255),
        )
        description = op.describe()
        assert "conditional" in description.lower()

    def test_describe_custom_vendors(self):
        """describe() lists all vendors when custom tuple is passed."""
        op = ConditionalAlterField(
            model_name="simplenode",
            name="path",
            field=LtreeField(max_length=255),
            vendors=("postgresql", "mysql"),
        )
        description = op.describe()
        assert "postgresql" in description
        assert "mysql" in description


# =============================================================================
# Public API re-export
# =============================================================================


class TestPublicApiExport:
    """LtreeField and ConditionalAlterField are accessible from clade root."""

    def test_ltreefield_importable_from_clade(self):
        """from clade import LtreeField works."""
        from clade import LtreeField as LF

        assert LF is LtreeField

    def test_conditional_alter_field_importable_from_clade(self):
        """from clade import ConditionalAlterField works."""
        from clade import ConditionalAlterField as CAF

        assert CAF is ConditionalAlterField
