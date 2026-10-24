"""Production startup checks compatibility; it never upgrades or creates schema."""
from sqlalchemy import inspect, text


def ensure_schema(engine, metadata, mode, expected_revision):
    if mode == 'bootstrap':
        # Existing development/test behavior, explicitly disabled by release config.
        metadata.create_all(bind=engine)
        return
    if mode != 'validate':
        raise RuntimeError('Unsupported schema management mode')
    with engine.connect() as connection:
        if engine.dialect.name == 'postgresql':
            connection.execute(text('SET TRANSACTION READ ONLY'))
        inspector = inspect(connection)
        if not inspector.has_table('alembic_version'):
            raise RuntimeError('Release requires an explicitly migrated database')
        versions = list(connection.execute(text('SELECT version_num FROM alembic_version')).scalars())
        if versions != [expected_revision]:
            raise RuntimeError('Release schema revision is incompatible; operator migration required')
        for table in metadata.sorted_tables:
            if not inspector.has_table(table.name):
                raise RuntimeError('Release schema table is missing')
            present = {column['name'] for column in inspector.get_columns(table.name)}
            if not {column.name for column in table.columns} <= present:
                raise RuntimeError('Release schema column is missing')
