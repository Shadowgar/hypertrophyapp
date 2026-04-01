# File-Based Structured Logging with Rotation

## Context

The Hypertrophy API currently uses Python's standard `logging` module with stdout-only output. The existing [`observability.py`](apps/api/app/observability.py) module provides a `log_event()` function that emits JSON-formatted log lines to stdout. This works for container logs but doesn't provide persistent file-based logging with rotation.

This plan adds file-based structured logging with size-based rotation while preserving the existing stdout logging for live container log viewing.

**WordPress-style debug logging**: Like WordPress's `define('WP_DEBUG', true); define('WP_DEBUG_LOG', true);` pattern, setting `LOG_LEVEL=DEBUG` in your config dumps all debug output to a file. Just flip the switch and restart - no Docker flags, no uvicorn changes, no code modifications.

## Current State

- **Framework**: FastAPI with uvicorn
- **Logging module**: [`apps/api/app/observability.py`](apps/api/app/observability.py)
- **Logger name**: `hypertrophy.app`
- **Current output**: stdout only (via `logging.basicConfig`)
- **Log format**: JSON objects via `log_event()` function
- **Config**: [`apps/api/app/config.py`](apps/api/app/config.py) using pydantic-settings
- **Docker**: [`docker-compose.yml`](docker-compose.yml) with api service

## Implementation Plan

### 1. Add `RotatingFileHandler` to observability.py

**File**: [`apps/api/app/observability.py`](apps/api/app/observability.py)

Add a `RotatingFileHandler` that writes to a file alongside the existing stdout handler. The handler will:
- Create the logs directory automatically if missing
- Use size-based rotation with configurable max bytes and backup count
- Write the same JSON format as stdout
- **Respect `LOG_LEVEL`**: Setting `LOG_LEVEL=DEBUG` writes debug output to the file without touching Docker flags

```python
import os
from logging.handlers import RotatingFileHandler

def setup_file_logging(
    log_file_path: str,
    log_level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> None:
    """Configure file-based logging with rotation.
    
    The file handler respects log_level, so setting LOG_LEVEL=DEBUG
    writes debug output to the file without modifying Docker flags.
    """
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Use the same formatter as stdout (no timestamp in log line since JSON includes it)
    formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
```

### 2. Add timestamp to log_event output

**File**: [`apps/api/app/observability.py`](apps/api/app/observability.py)

Add an ISO 8601 UTC timestamp to every log event:

```python
from datetime import datetime, timezone

def log_event(event: str, level: str = "info", **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "event": event,
    }
    # ... rest of existing logic
```

### 3. Add logging config to Settings

**File**: [`apps/api/app/config.py`](apps/api/app/config.py)

Add environment variable configuration for logging:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Logging configuration
    log_level: str = "INFO"
    log_file_path: str = "logs/app-debug.log"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5
```

**Usage**: Set `LOG_LEVEL=DEBUG` in `.env` or `docker-compose.yml` to see debug output in the log file. No Docker flags or uvicorn changes needed.

### 4. Initialize file logging at startup

**File**: [`apps/api/app/main.py`](apps/api/app/main.py)

Call `setup_file_logging()` during app startup using the lifespan context manager:

```python
from .observability import log_event, setup_file_logging, validation_failure_event_name

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    setup_file_logging(
        log_file_path=settings.log_file_path,
        log_level=settings.log_level,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )
    yield
```

### 5. Update Docker configuration

**File**: [`docker-compose.yml`](docker-compose.yml)

Add environment variables and a volume mount for the logs directory:

```yaml
services:
  api:
    environment:
      # ... existing vars ...
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      LOG_FILE_PATH: ${LOG_FILE_PATH:-/app/logs/app-debug.log}
      LOG_MAX_BYTES: ${LOG_MAX_BYTES:-5000000}
      LOG_BACKUP_COUNT: ${LOG_BACKUP_COUNT:-5}
    volumes:
      - api_logs:/app/logs
```

Add the volume definition:

```yaml
volumes:
  postgres_data:
  api_logs:
```

### 6. Update Dockerfile

**File**: [`apps/api/Dockerfile`](apps/api/Dockerfile)

Create the logs directory in the container:

```dockerfile
WORKDIR /app/apps/api
RUN mkdir -p /app/logs
EXPOSE 8000
```

## Files Changed

| File | Change |
|------|--------|
| [`apps/api/app/observability.py`](apps/api/app/observability.py) | Add `setup_file_logging()`, add timestamp to `log_event()` |
| [`apps/api/app/config.py`](apps/api/app/config.py) | Add `log_level`, `log_file_path`, `log_max_bytes`, `log_backup_count` fields |
| [`apps/api/app/main.py`](apps/api/app/main.py) | Call `setup_file_logging()` in lifespan |
| [`apps/api/Dockerfile`](apps/api/Dockerfile) | Create `/app/logs` directory |
| [`docker-compose.yml`](docker-compose.yml) | Add logging env vars and `api_logs` volume |

## Environment Variables Added

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FILE_PATH` | `logs/app-debug.log` (relative) or `/app/logs/app-debug.log` (Docker) | Path to the log file |
| `LOG_MAX_BYTES` | `5000000` (5 MB) | Maximum log file size before rotation |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated backup files to keep |

## Log Format

Each log line is a single JSON object with these fields:

```json
{
  "timestamp": "2026-04-01T05:12:35.009Z",
  "level": "INFO",
  "event": "week_generate_requested",
  "route": "/plan/generate-week",
  "action": "post",
  "user_id": "usr_abc123",
  "selected_program_id": "phase1_full_body",
  "template_id": "phase1_full_body_v2",
  "runtime_template_id": "generated_full_body_v1",
  "path_family": "generated_full_body",
  "generation_mode": "current_week_regenerate",
  "week_index": 3,
  "authored_week_index": 3,
  "target_days": 4,
  "session_id": null,
  "error_class": null,
  "error_message": null
}
```

Fields not present in a given event are omitted from the JSON (not emitted as null).

## Safety: Secret Redaction

The existing `_sanitize()` function in [`observability.py`](apps/api/app/observability.py) already handles type coercion. No secrets, tokens, passwords, or auth headers are passed to `log_event()` in the current codebase. The function signature uses explicit keyword arguments rather than `**kwargs` from request objects, so accidental secret leakage is structurally prevented.

**Verification**: Search for `log_event` calls and confirm none pass `request.headers`, `request.body`, or password fields.

## Scope: Endpoints Covered

The following endpoints already use `log_event()` and will automatically benefit from file logging:

| Endpoint | Event Name | File |
|----------|------------|------|
| Onboarding submit | `onboarding_submitted` | [`profile.py:363`](apps/api/app/routers/profile.py:363) |
| Profile update | `profile_updated` | [`profile.py:363`](apps/api/app/routers/profile.py:363) |
| Adaptation preview | `frequency_adaptation_preview_requested/completed` | [`plan.py:920,972`](apps/api/app/routers/plan.py:920) |
| Adaptation apply | `frequency_adaptation_apply_requested/completed` | [`plan.py:1001,1060`](apps/api/app/routers/plan.py:1001) |
| Week generate | `week_generate_requested`, `week_regenerated_current` | [`plan.py:1418,1449`](apps/api/app/routers/plan.py:1418) |
| Week next | `week_next_requested`, `week_advanced_next` | [`plan.py:1418,1449`](apps/api/app/routers/plan.py:1418) |
| Latest week fetch | `latest_week_fetched` | [`plan.py:1538`](apps/api/app/routers/plan.py:1538) |
| Today workout fetch | `today_workout_fetched` | [`workout.py:200`](apps/api/app/routers/workout.py:200) |
| Workout progress fetch | `workout_progress_fetched` | [`workout.py:407`](apps/api/app/routers/workout.py:407) |
| Validation failures | `*_failed_validation` | [`main.py:36`](apps/api/app/main.py:36) |
| Unhandled exceptions | `request_failed_exception` | [`main.py:53`](apps/api/app/main.py:53) |
| Weekly review | `weekly_review_submitted` | [`profile.py:574`](apps/api/app/routers/profile.py:574) |

## Commands

### Watch live logs (stdout)
```bash
docker logs -f hypertrophy-api
```

### Watch file-based logs
```bash
docker exec hypertrophy-api tail -f /app/logs/app-debug.log
```

### Inspect rotated backups
```bash
docker exec hypertrophy-api ls -la /app/logs/
# Shows: app-debug.log, app-debug.log.1, app-debug.log.2, ..., app-debug.log.5
```

### Read a specific backup
```bash
docker exec hypertrophy-api cat /app/logs/app-debug.log.1
```

### Copy logs out of container
```bash
docker cp hypertrophy-api:/app/logs/ ./local-logs/
```

## Verification

1. Start the API with `docker-compose up`
2. Make a request to any covered endpoint
3. Verify stdout shows the JSON log line
4. Verify the file contains the same JSON log line:
   ```bash
   docker exec hypertrophy-api cat /app/logs/app-debug.log
   ```
5. Generate enough logs to trigger rotation (>5 MB)
6. Verify backup files exist:
   ```bash
   docker exec hypertrophy-api ls -la /app/logs/
   ```
