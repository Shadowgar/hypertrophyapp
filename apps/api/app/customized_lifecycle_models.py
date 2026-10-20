"""Isolated account-owned candidate commands; no activation schema or client authority."""
from dataclasses import dataclass
from typing import Literal, Protocol
from contextlib import AbstractContextManager
from pydantic import Field, StrictBool, StrictInt

from .customized_preview_models import PreviewRequest, StrictPreviewModel


class ProposalRequest(PreviewRequest):
    # These inherited fields are internal compatibility values only. The lifecycle
    # rejects their presence at its public boundary and supplies server references.
    audience: Literal["synthetic_review_preview", "customized_program"] = "synthetic_review_preview"
    mode: Literal["customized"]
    consent: StrictBool = True
    consent_reference: str = "server_preview_permission_only"


class AcceptCommand(StrictPreviewModel):
    expected_revision: StrictInt = Field(ge=1)
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    challenge: str = Field(min_length=20, max_length=128)
    terms_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    acknowledgements: tuple[str, ...] = Field(max_length=96)
    mode: Literal["customized"]
    agree: StrictBool


class CompactAcceptCommand(StrictPreviewModel):
    protocol: Literal["compact-candidate-consent-v2"]
    expected_revision: StrictInt = Field(ge=1)
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    challenge: str = Field(min_length=20, max_length=128)
    terms_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    mode: Literal["customized"]
    agree: StrictBool


@dataclass(frozen=True)
class AccountActor:
    subject: str
    session_id: str
    scopes: tuple[str, ...]
    authorization_revision: str | None = None


class LifecycleError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status
        super().__init__(code)


class ProposalTransaction(Protocol):
    def read(self, subject: str, proposal_id: str) -> dict | None: ...
    def history(self, subject: str, proposal_id: str) -> list[dict]: ...
    def append(self, subject: str, document: dict, expected_revision: int) -> None: ...
    def retry(self, subject: str, key: str) -> tuple[str, dict] | None: ...
    def remember(self, subject: str, key: str, digest: str, response: dict) -> None: ...


class ProposalStore(Protocol):
    def transaction(self) -> AbstractContextManager[ProposalTransaction]: ...
