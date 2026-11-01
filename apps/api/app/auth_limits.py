"""Bound public credential work in the current single-process API deployment.

All ingress paths share a process-wide budget. Account/token fingerprints limit
repeated targets without retaining raw identifiers. State is bounded and expires;
it is not a distributed limiter and restarts clear it. Multiple API workers need
a shared limiter or qualified ingress enforcement before scaling.
"""
from collections import deque
from hashlib import sha256
from math import ceil
from threading import BoundedSemaphore, Lock
from time import monotonic

from fastapi import HTTPException


def _rejected(retry_after: float = 60) -> HTTPException:
    return HTTPException(status_code=429, detail="Too many authentication attempts; try again later", headers={"Retry-After": str(max(1, ceil(retry_after)))})


class AuthAttemptLimiter:
    policies = {"login": (10, 60), "register": (5, 60), "request": (3, 900), "confirm": (5, 60), "recovery_generate": (3, 900)}

    def __init__(self, *, clock=monotonic, max_targets=2048):
        self.clock, self.max_targets = clock, max_targets
        self.lock = Lock()
        self.global_attempts = deque()
        self.targets = {}

    def check(self, operation: str, identity: str) -> None:
        limit, window = self.policies[operation]
        key = (operation, sha256(identity.encode("utf-8")).digest())
        with self.lock:
            now = self.clock()
            while self.global_attempts and self.global_attempts[0] <= now - 60:
                self.global_attempts.popleft()
            if len(self.global_attempts) >= 60:
                raise _rejected(self.global_attempts[0] + 60 - now)
            self.targets = {k: value for k, value in self.targets.items() if value[1] > now}
            attempts, _ = self.targets.get(key, (deque(), now + window))
            while attempts and attempts[0] <= now - window:
                attempts.popleft()
            if len(attempts) >= limit:
                raise _rejected(attempts[0] + window - now)
            if key not in self.targets and len(self.targets) >= self.max_targets:
                raise _rejected()
            # Target-rejected traffic must not spend other accounts' shared
            # expensive-work budget. Random targets still share this ceiling.
            self.global_attempts.append(now)
            attempts.append(now)
            self.targets[key] = (attempts, now + window)


auth_attempts = AuthAttemptLimiter()
_credential_slots = BoundedSemaphore(4)


def limit_auth_concurrency():
    if not _credential_slots.acquire(blocking=False):
        raise _rejected(1)
    try:
        yield
    finally:
        _credential_slots.release()
