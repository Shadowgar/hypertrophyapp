from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .config import settings
from .knowledge_schema import (
    CanonicalExerciseLibraryBundle,
    CompiledKnowledgeManifest,
    DoctrineBundle,
    ExerciseMetadataV2Bundle,
    PolicyBundle,
    SourceRegistryBundle,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_COMPILED_DIR = REPO_ROOT / "knowledge" / "compiled"

T = TypeVar("T", bound=BaseModel)


def _is_allowed_compiled_dir(path: Path) -> bool:
    return path.name == "compiled" and path.parent.name == "knowledge"


def _resolve_compiled_dir(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        resolved = base_dir.resolve()
        if not _is_allowed_compiled_dir(resolved):
            raise ValueError(f"compiled knowledge base_dir must point to a knowledge/compiled directory: {resolved}")
        return resolved

    configured = Path(settings.compiled_knowledge_dir).resolve()
    if _is_allowed_compiled_dir(configured) and configured.exists():
        return configured

    return REPO_COMPILED_DIR


def _load_model(path: Path, model_type: type[T]) -> T:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return model_type.model_validate(payload)


def load_compiled_manifest(base_dir: Path | None = None) -> CompiledKnowledgeManifest:
    compiled_dir = _resolve_compiled_dir(base_dir)
    return _load_model(compiled_dir / "build_manifest.v1.json", CompiledKnowledgeManifest)


def load_source_registry(base_dir: Path | None = None) -> SourceRegistryBundle:
    compiled_dir = _resolve_compiled_dir(base_dir)
    return _load_model(compiled_dir / "source_registry.v1.json", SourceRegistryBundle)


def load_exercise_library(base_dir: Path | None = None) -> CanonicalExerciseLibraryBundle:
    compiled_dir = _resolve_compiled_dir(base_dir)
    return _load_model(compiled_dir / "exercise_library.foundation.v1.json", CanonicalExerciseLibraryBundle)


def load_exercise_metadata_v2(base_dir: Path | None = None) -> ExerciseMetadataV2Bundle | None:
    compiled_dir = _resolve_compiled_dir(base_dir)
    path = compiled_dir / "exercise_library.metadata.v2.json"
    if not path.exists():
        return None
    return _load_model(path, ExerciseMetadataV2Bundle)


def load_doctrine_bundle(bundle_id: str, base_dir: Path | None = None) -> DoctrineBundle:
    compiled_dir = _resolve_compiled_dir(base_dir)
    path = compiled_dir / "doctrine_bundles" / f"{bundle_id}.bundle.json"
    return _load_model(path, DoctrineBundle)


def load_policy_bundle(bundle_id: str, base_dir: Path | None = None) -> PolicyBundle:
    compiled_dir = _resolve_compiled_dir(base_dir)
    path = compiled_dir / "policy_bundles" / f"{bundle_id}.bundle.json"
    return _load_model(path, PolicyBundle)
