"""Relational proposal contracts shared by the existing PostgreSQL adapter."""
from sqlalchemy import Table, Column, String, Integer, JSON, Boolean, DateTime, ForeignKey, ForeignKeyConstraint, CheckConstraint, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base

m=Base.metadata
Table('customized_candidate_schema',m,Column('version',Integer,primary_key=True),CheckConstraint('version=1'))
Table('customized_candidate_sessions',m,
    Column('session_id',Uuid(as_uuid=False),primary_key=True),Column('subject',String,ForeignKey('users.id'),nullable=False),
    Column('credential_fingerprint',String(64),nullable=False,unique=True),Column('credential_digest',String(64),nullable=False),
    Column('revision',Integer,nullable=False),Column('entitlement_reference',String,nullable=False),Column('scopes',JSON().with_variant(JSONB,'postgresql'),nullable=False),
    Column('valid_from',DateTime(timezone=True),nullable=False),Column('expires_at',DateTime(timezone=True),nullable=False),
    Column('revoked',Boolean,nullable=False,server_default='false'),UniqueConstraint('subject','session_id'),
    CheckConstraint('revision>0'),CheckConstraint('expires_at>valid_from'))
Table('customized_candidate_events',m,Column('subject',String,ForeignKey('users.id'),primary_key=True),
    Column('proposal_id',String,primary_key=True),Column('revision',Integer,primary_key=True),Column('document',JSON().with_variant(JSONB,'postgresql'),nullable=False),
    Column('previous_digest',String(64),nullable=False),Column('digest',String(64),nullable=False),CheckConstraint('revision>0'))
Table('customized_candidate_heads',m,Column('subject',String,primary_key=True),Column('proposal_id',String,primary_key=True),
    Column('revision',Integer,nullable=False),Column('digest',String(64),nullable=False),CheckConstraint('revision>0'),
    ForeignKeyConstraint(['subject','proposal_id','revision'],['customized_candidate_events.subject','customized_candidate_events.proposal_id','customized_candidate_events.revision']))
Table('customized_candidate_commands',m,Column('subject',String,ForeignKey('users.id'),primary_key=True),
    Column('request_key',String(96),primary_key=True),Column('digest',String(64),nullable=False),Column('response',JSON().with_variant(JSONB,'postgresql'),nullable=False))
