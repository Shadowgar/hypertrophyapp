"""Explicit staged factory. No production main registration or implicit grants."""
from .customized_lifecycle_http import create_lifecycle_app
from .customized_staging_auth import staging_account_dependency
from .customized_consent_summary import COMPACT_PROTOCOL
from .customized_lifecycle_models import LifecycleError


def create_staging_app(*,service=None,access_gate=None,trusted_origin=None,initial_request=None):
    def unavailable():raise LifecycleError('entitlement_required',403)
    if service is not None and access_gate is not None:
        service.authorize_actor=access_gate.authorize
    return create_lifecycle_app(service=service,
        account_dependency=staging_account_dependency(access_gate) if access_gate is not None else unavailable,
        trusted_origin=trusted_origin,initial_request=initial_request,consent_protocol=COMPACT_PROTOCOL)
