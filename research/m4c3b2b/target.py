"""Explicit allowlisted target, with out-of-band identity + random marker checks."""
import json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL


def open_target(manifest):
    path=Path(manifest)
    if path.is_symlink() or not path.resolve().is_relative_to(Path('/tmp')):
        raise ValueError('Explicit local disposable manifest required')
    m=json.loads(path.read_text())
    if (m.get('host')!='127.0.0.1' or m.get('user')!='c3b2b_owner'
            or not m.get('database','').startswith('c3b2b97_') or len(m.get('marker',''))!=64
            or type(m.get('port')) is not int or not 1024<m['port']<65536):
        raise ValueError('Target is not allowlisted')
    engine=create_engine(URL.create('postgresql+psycopg',username=m['user'],password=m['password'],
        host=m['host'],port=m['port'],database=m['database']),pool_size=4,max_overflow=4)
    try:
        with engine.connect() as conn:
            identity=conn.execute(text('SELECT current_database(),current_user')).first()
            if tuple(identity)!=(m['database'],m['user']):raise ValueError('Target identity mismatch')
            marker=conn.execute(text('SELECT marker FROM c3b2b_disposable_marker')).scalar_one()
            if marker!=m['marker']:raise ValueError('Disposable marker mismatch')
    except BaseException:
        engine.dispose();raise
    return engine
