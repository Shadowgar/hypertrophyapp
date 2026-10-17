"""Unregistered PostgreSQL candidate adapter; no URL discovery or schema writes.

The caller must provide an explicitly verified disposable Engine. The account row
is the lock owner used by #83/history. All command/auth/calendar operations share
one connection; no global mutable authorization or connection cache exists.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import json
from uuid import UUID,uuid4

from sqlalchemy import text
from core_engine.customized.audit import content_hash
from .customized_lifecycle_models import AccountActor,LifecycleError

SCOPES=frozenset(('customized:preview','customized:proposal'))


class PostgresUnit:
    def __init__(self,engine):
        self.engine=engine
        self._active=ContextVar('customized_pg_connection_'+uuid4().hex,default=None)

    @contextmanager
    def account(self,subject):
        active=self._active.get()
        if active is not None:
            if active[0]!=subject:raise LifecycleError('account_context_mismatch',403)
            yield active[1];return
        with self.engine.begin() as conn:
            conn.execute(text("SET LOCAL lock_timeout='3s'"))
            conn.execute(text("SET LOCAL statement_timeout='10s'"))
            user=conn.execute(text('SELECT id FROM users WHERE id=:s FOR UPDATE'),{'s':subject}).first()
            if user is None:raise LifecycleError('authentication_required',401)
            token=self._active.set((subject,conn))
            try:yield conn
            finally:self._active.reset(token)

    def connection(self,subject):
        active=self._active.get()
        if active is None or active[0]!=subject:raise LifecycleError('account_transaction_required',503)
        return active[1]


class PostgresSessionGate:
    """Server-generated session identity, explicit entitlement and locked revocation.

    Token fingerprint is a lookup credential only, never the session identity or
    scope authority. Actual JWT verification remains in get_current_user. The host
    must provision sessions explicitly after that verifier, not from client claims.
    """
    def __init__(self,unit,*,clock):self.unit,self.clock=unit,clock

    def issue(self,subject,authorization_header,*,entitlement_reference,scopes,valid_from,expires_at):
        # Trusted server provisioning only; no HTTP route or JWT scope consumption.
        if (not entitlement_reference or not SCOPES<=set(scopes)
                or not isinstance(authorization_header,str) or not authorization_header.startswith('Bearer ')
                or not 8<len(authorization_header)<=8192 or valid_from.tzinfo is None
                or expires_at.tzinfo is None or not valid_from<=self.clock()<expires_at):
            raise LifecycleError('explicit_session_entitlement_required',403)
        id=str(uuid4())
        with self.unit.account(subject) as conn:
            password=conn.execute(text('SELECT password_hash FROM users WHERE id=:s'),dict(s=subject)).scalar_one()
            conn.execute(text("""INSERT INTO customized_candidate_sessions(session_id,subject,credential_fingerprint,
                credential_digest,revision,entitlement_reference,scopes,valid_from,expires_at,revoked)
                VALUES (:id,:s,:f,:d,1,:e,CAST(:scopes AS jsonb),:start,:end,false)"""),
                dict(id=id,s=subject,f=sha256(authorization_header.encode()).hexdigest(),d=sha256(password.encode()).hexdigest(),
                    e=entitlement_reference,scopes=json.dumps(list(scopes)),start=valid_from,end=expires_at))
        return id

    def revoke(self,subject,session_id=None):
        # Same User-first lock as candidate commits, #83 and credential UPDATE.
        with self.unit.account(subject) as conn:
            conn.execute(text("""UPDATE customized_candidate_sessions SET revoked=true,revision=revision+1
                WHERE subject=:s AND (CAST(:id AS uuid) IS NULL OR session_id=CAST(:id AS uuid))"""),dict(s=subject,id=session_id))

    def _row(self,conn,subject,session_id):
        try:UUID(str(session_id))
        except (ValueError,TypeError,AttributeError):raise LifecycleError('session_unavailable',401) from None
        row=conn.execute(text('''SELECT s.*,u.password_hash FROM customized_candidate_sessions s
            JOIN users u ON u.id=s.subject WHERE s.subject=:s AND s.session_id=:id'''),dict(s=subject,id=session_id)).mappings().first()
        if row is None:raise LifecycleError('entitlement_required',403)
        if (row['revoked'] or not row['valid_from']<=self.clock()<row['expires_at']
                or sha256(row['password_hash'].encode()).hexdigest()!=row['credential_digest']):
            raise LifecycleError('session_unavailable',401)
        if not row['entitlement_reference'] or not SCOPES<=set(row['scopes']):raise LifecycleError('capability_required',403)
        return row

    @staticmethod
    def _revision(row):
        return content_hash({k:(str(v) if k=='session_id' else v) for k,v in row.items() if k!='password_hash'})

    def bind(self,user,authorization_header):
        fingerprint=sha256(authorization_header.encode()).hexdigest()
        with self.unit.account(user.id) as conn:
            session_id=conn.execute(text('''SELECT session_id FROM customized_candidate_sessions
                WHERE subject=:s AND credential_fingerprint=:f'''),dict(s=user.id,f=fingerprint)).scalar()
            if session_id is None:raise LifecycleError('entitlement_required',403)
            row=self._row(conn,user.id,session_id)
            return AccountActor(user.id,str(session_id),tuple(row['scopes']),self._revision(row))

    def authorize(self,actor):
        with self.unit.account(actor.subject) as conn:
            row=self._row(conn,actor.subject,actor.session_id)
            if actor.authorization_revision!=self._revision(row):raise LifecycleError('stale_session_grant',401)


class PostgresProposalStore:
    def __init__(self,unit,gate):
        if gate.unit is not unit:raise ValueError('Same transactional authority required')
        self.unit,self.gate=unit,gate

    @contextmanager
    def authorized_transaction(self,actor):
        with self.unit.account(actor.subject) as conn:
            self.gate.authorize(actor)
            yield _Transaction(conn,actor.subject)
            self.gate.authorize(actor)

    def transaction(self):
        raise LifecycleError('account_transaction_required',503)


class _Transaction:
    def __init__(self,connection,subject):self.connection,self.subject=connection,subject
    def _owned(self,subject):
        if subject!=self.subject:raise LifecycleError('not_found',404)

    def history(self,subject,proposal_id):
        self._owned(subject)
        rows=self.connection.execute(text('''SELECT revision,document,previous_digest,digest FROM customized_candidate_events
            WHERE subject=:s AND proposal_id=:p ORDER BY revision'''),dict(s=subject,p=proposal_id)).mappings()
        result=[];previous=''
        for row in rows:
            document=row['document']
            expected=content_hash((previous,document))
            if (row['revision']!=len(result)+1 or document['revision']!=row['revision']
                    or document['subject']!=subject or document['proposal_id']!=proposal_id
                    or row['previous_digest']!=previous or row['digest']!=expected):
                raise LifecycleError('candidate_replay_integrity',503)
            result.append(document);previous=row['digest']
        head=self.connection.execute(text("""SELECT revision,digest FROM customized_candidate_heads
            WHERE subject=:s AND proposal_id=:p"""),dict(s=subject,p=proposal_id)).first()
        if (head is None and result) or (head is not None and (head.revision!=len(result) or head.digest!=previous)):
            raise LifecycleError('candidate_replay_integrity',503)
        return result

    def read(self,subject,proposal_id):
        rows=self.history(subject,proposal_id)
        return rows[-1] if rows else None

    def append(self,subject,document,expected_revision):
        rows=self.history(subject,document['proposal_id']);revision=len(rows)
        if revision!=expected_revision or document['revision']!=revision+1:raise LifecycleError('stale_revision')
        previous=''
        for row in rows:previous=content_hash((previous,row))
        self.connection.execute(text('''INSERT INTO customized_candidate_events
            (subject,proposal_id,revision,document,previous_digest,digest)
            VALUES (:s,:p,:r,CAST(:d AS jsonb),:prev,:digest)'''),
            dict(s=subject,p=document['proposal_id'],r=document['revision'],d=json.dumps(document),prev=previous,digest=content_hash((previous,document))))

        head=self.connection.execute(text("""INSERT INTO customized_candidate_heads(subject,proposal_id,revision,digest)
            VALUES (:s,:p,:r,:d) ON CONFLICT(subject,proposal_id) DO UPDATE SET revision=EXCLUDED.revision,digest=EXCLUDED.digest
            WHERE customized_candidate_heads.revision=:expected AND customized_candidate_heads.digest=:previous
            RETURNING revision"""),dict(s=subject,p=document['proposal_id'],r=document['revision'],
                d=content_hash((previous,document)),expected=expected_revision,previous=previous)).scalar()
        if head!=document['revision']:raise LifecycleError('stale_revision')

    def retry(self,subject,key):
        self._owned(subject)
        row=self.connection.execute(text('''SELECT digest,response FROM customized_candidate_commands
            WHERE subject=:s AND request_key=:k'''),dict(s=subject,k=key)).first()
        return (row.digest,row.response) if row else None

    def remember(self,subject,key,digest,response):
        self._owned(subject)
        self.connection.execute(text('''INSERT INTO customized_candidate_commands(subject,request_key,digest,response)
            VALUES (:s,:k,:d,CAST(:r AS jsonb))'''),dict(s=subject,k=key,d=digest,r=json.dumps(response)))
