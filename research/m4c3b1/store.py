"""Append-only disposable SQLite adapter. No app ORM, migrations or reset helpers.

Only explicitly created, marked files under a caller-declared disposable /tmp
root can be opened. This qualifies synthetic local transactions, not PostgreSQL.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from app.customized_lifecycle_models import LifecycleError


class DisposableProposalStore:
    def __init__(self, path, root):
        self.path, self.root = Path(path), Path(root)

    @classmethod
    def _target(cls,path,disposable_root):
        path, root=Path(path).absolute(),Path(disposable_root).resolve()
        if (not root.is_relative_to(Path('/tmp')) or root==Path('/tmp')
                or path.is_symlink() or not path.parent.resolve().is_relative_to(root)
                or path.suffix!='.sqlite'):
            raise ValueError("Explicit disposable SQLite file under a /tmp task root required")
        return cls(path,root)

    @classmethod
    def create(cls,path,*,disposable_root):
        store=cls._target(path,disposable_root)
        # Exclusive creation prevents treating an existing database as disposable.
        with store.path.open('xb'):
            pass
        with sqlite3.connect(store.path) as db:
            db.execute('CREATE TABLE c3b1_marker (version TEXT NOT NULL)')
            db.execute("INSERT INTO c3b1_marker VALUES ('synthetic-disposable-only-v1')")
            db.execute('CREATE TABLE proposal_events (subject TEXT NOT NULL, proposal_id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, PRIMARY KEY(subject,proposal_id,revision))')
            db.execute('CREATE TABLE proposal_retries (subject TEXT NOT NULL, request_key TEXT NOT NULL, digest TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(subject,request_key))')
        store.path.chmod(0o600)
        return store

    @classmethod
    def open(cls,path,*,disposable_root):
        store=cls._target(path,disposable_root)
        if not store.path.is_file():
            raise ValueError("Existing marked disposable store required")
        with sqlite3.connect(store.path) as db:
            if db.execute('SELECT version FROM c3b1_marker').fetchall()!=[('synthetic-disposable-only-v1',)]:
                raise ValueError("Disposable marker required")
        return store

    @contextmanager
    def transaction(self):
        # BEGIN IMMEDIATE serializes read/CAS/append/retry across distinct handles.
        db=sqlite3.connect(self.path,timeout=5)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield _Transaction(db)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()


class _Transaction:
    def __init__(self,db): self.db=db

    def read(self,subject,proposal_id):
        row=self.db.execute('SELECT document FROM proposal_events WHERE subject=? AND proposal_id=? ORDER BY revision DESC LIMIT 1',(subject,proposal_id)).fetchone()
        return json.loads(row[0]) if row else None

    def history(self,subject,proposal_id):
        return [json.loads(row[0]) for row in self.db.execute('SELECT document FROM proposal_events WHERE subject=? AND proposal_id=? ORDER BY revision',(subject,proposal_id))]

    def append(self,subject,document,expected_revision):
        current=self.read(subject,document['proposal_id'])
        if (current['revision'] if current else 0)!=expected_revision or document['revision']!=expected_revision+1:
            raise LifecycleError('stale_revision')
        self.db.execute('INSERT INTO proposal_events VALUES (?,?,?,?)',(subject,document['proposal_id'],document['revision'],json.dumps(document,sort_keys=True,allow_nan=False)))

    def retry(self,subject,key):
        row=self.db.execute('SELECT digest,response FROM proposal_retries WHERE subject=? AND request_key=?',(subject,key)).fetchone()
        return (row[0],json.loads(row[1])) if row else None

    def remember(self,subject,key,digest,response):
        self.db.execute('INSERT INTO proposal_retries VALUES (?,?,?,?)',(subject,key,digest,json.dumps(response,sort_keys=True,allow_nan=False)))
