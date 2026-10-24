"""Actual SQLite metadata checks, only in a new explicit temporary test target."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('schema_management',ROOT/'apps/api/app/schema_management.py')
schema=importlib.util.module_from_spec(spec);spec.loader.exec_module(schema)


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='workoutapp-schema-test-')
        file=Path(self.temp.name)/'explicit.sqlite3'
        self.engine=create_engine('sqlite:///'+str(file))
        assert self.engine.url.database==str(file) and not file.exists()
        self.metadata=MetaData();self.table=Table('synthetic_history',self.metadata,Column('id',Integer,primary_key=True),Column('value',String))
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE alembic_version (version_num TEXT NOT NULL)'))
            c.execute(text("INSERT INTO alembic_version VALUES ('0026_initial_calibration')"))
            c.execute(text('CREATE TABLE synthetic_history (id INTEGER PRIMARY KEY, value TEXT)'))
            c.execute(text("INSERT INTO synthetic_history VALUES (1,'synthetic-preserved')"))

    def tearDown(self):self.engine.dispose();self.temp.cleanup()

    def test_validation_never_calls_ddl_and_preserves_existing_rows(self):
        with patch.object(self.metadata,'create_all',side_effect=AssertionError('DDL forbidden')):
            schema.ensure_schema(self.engine,self.metadata,'validate','0026_initial_calibration')
        with self.engine.connect() as c:self.assertEqual(c.execute(text('SELECT value FROM synthetic_history')).scalar(),'synthetic-preserved')

    def test_wrong_revision_and_unknown_mode_fail_without_creation(self):
        with patch.object(self.metadata,'create_all',side_effect=AssertionError('DDL forbidden')):
            for mode,revision in (('validate','0025_interface_preferences'),('unknown','0026_initial_calibration')):
                with self.assertRaises(RuntimeError):schema.ensure_schema(self.engine,self.metadata,mode,revision)

    def test_missing_table_or_column_fails_without_repair(self):
        for column_only in (False,True):
            metadata=MetaData()
            Table('synthetic_history' if column_only else 'missing',metadata,Column('missing_column',String))
            with patch.object(metadata,'create_all',side_effect=AssertionError('DDL forbidden')):
                with self.assertRaises(RuntimeError):schema.ensure_schema(self.engine,metadata,'validate','0026_initial_calibration')

    def test_existing_bootstrap_mode_remains_available_for_explicit_development(self):
        metadata=MetaData();Table('new_synthetic_table',metadata,Column('id',Integer,primary_key=True))
        schema.ensure_schema(self.engine,metadata,'bootstrap','unused')
        with self.engine.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM new_synthetic_table')).scalar(),0)


if __name__=='__main__':unittest.main()
