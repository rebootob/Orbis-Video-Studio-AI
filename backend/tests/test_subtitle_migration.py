import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "021_core_v1_subtitles.py"
    )
    spec = importlib.util.spec_from_file_location("migration_021_core_v1_subtitles", migration_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _column_names(connection):
    return {column["name"] for column in sa.inspect(connection).get_columns("assembly_timelines")}


def test_subtitle_migration_upgrade_downgrade_upgrade_lifecycle():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "assembly_timelines",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    metadata.create_all(engine)

    migration = _load_migration_module()

    with engine.begin() as connection:
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})
        migration.op = Operations(context)

        migration.upgrade()
        assert "subtitle_state" in _column_names(connection)

        migration.downgrade()
        assert "subtitle_state" not in _column_names(connection)

        migration.upgrade()
        assert "subtitle_state" in _column_names(connection)
