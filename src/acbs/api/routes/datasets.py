from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from acbs.api.deps import get_session
from acbs.api.schemas import DatasetUploadResponse
from acbs.data.loader import load_local
from acbs.data.profiler import profile_dataset
from acbs.data.target_detection import detect_target_in_file
from acbs.exceptions import DatasetError
from acbs.storage.models import ExperimentRow
from acbs.storage.repository import Repository
from acbs.utils.paths import repo_root, settings

router = APIRouter(prefix="/datasets", tags=["datasets"])
_UPLOAD_LOCK = threading.Lock()
UPLOAD_DIR = repo_root() / "data" / "raw"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Streamed uploads are written in 1 MiB chunks; the size cap is enforced
# incrementally so an oversized file is rejected without ever being fully
# buffered in RAM.
_CHUNK = 1024 * 1024


def _unlink(path: str | Path) -> None:
    """Best-effort removal of a temp file; ignores missing files."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


@router.get("")
def list_datasets(session: Session = Depends(get_session)):
    repo = Repository(session)
    return [
        {
            "id": d.id,
            "name": d.name,
            "source": d.source,
            "n_rows": d.n_rows,
            "n_features": d.n_features,
        }
        for d in repo.list_datasets()
    ]


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int, session: Session = Depends(get_session)):
    row = Repository(session).get_dataset(dataset_id)
    if not row:
        raise HTTPException(404, "dataset not found")
    return {
        "id": row.id,
        "name": row.name,
        "source": row.source,
        "profile": row.profile_json,
    }


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    force: bool = Query(False),
    session: Session = Depends(get_session),
):
    """Delete a dataset.

    Refuses with 409 when experiments reference the dataset unless ``force=1``,
    which cascades and deletes dependent experiments too. The raw file is always
    removed.
    """
    repo = Repository(session)
    row = repo.delete_dataset(dataset_id, force=force)
    if row is None:
        dependent = session.query(ExperimentRow).filter_by(dataset_id=dataset_id).first()
        if dependent is not None:
            raise HTTPException(
                409,
                "dataset is referenced by experiments; use force=1 to cascade",
            )
        raise HTTPException(404, "dataset not found")
    return {"ok": True, "deleted": row.id, "name": row.name}


@router.post("", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    target: str | None = None,
    session: Session = Depends(get_session),
):
    max_bytes = int(settings.max_upload_mb) * 1024 * 1024
    name = Path(file.filename or "upload.csv").name.replace("..", "")

    # Stream to a temp file in the upload dir, enforcing the size cap
    # incrementally and computing the digest as bytes arrive. The file never
    # lives fully in RAM and an oversized upload is rejected early.
    hasher = hashlib.sha256()
    total = 0
    fd, tmp_path = tempfile.mkstemp(dir=UPLOAD_DIR, prefix=".upload-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp:
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(413, "file too large")
                hasher.update(chunk)
                tmp.write(chunk)
        dest = UPLOAD_DIR / name
        os.replace(tmp_path, dest)
    except HTTPException:
        _unlink(tmp_path)
        raise
    except Exception:
        _unlink(tmp_path)
        raise

    digest = hasher.hexdigest()
    repo = Repository(session)
    existing = repo.get_dataset_by_hash(digest)
    if existing:
        existing_meta = (existing.profile_json or {}).get("meta") or {}
        stored_file = repo_root() / "data" / "raw" / existing.name
        if existing_meta.get("target_column") == target and stored_file.exists():
            return DatasetUploadResponse(
                id=existing.id,
                name=existing.name,
                profile=existing.profile_json or {},
                warnings=(existing.profile_json or {}).get("warnings", []),
                target=target,
                target_source=(existing_meta.get("target_source") or "explicit"),
            )
        # Same bytes but a different target (or the stored copy is gone):
        # repoint the existing row at this upload instead of returning a
        # dataset whose backing file no longer exists.

    # Detect the target from the file on disk (bounded row sample) instead of
    # re-parsing the full in-memory bytes.
    target_source = "explicit"
    if not target:
        try:
            target = detect_target_in_file(dest)
        except DatasetError as exc:
            raise HTTPException(400, str(exc)) from exc
        target_source = "auto"

    try:
        loaded = load_local(dest, target)
    except DatasetError as exc:
        raise HTTPException(400, str(exc)) from exc
    profile = profile_dataset(loaded.X, loaded.y)
    profile_json = {
        **profile.model_dump(),
        # ``meta`` must carry the target column: ``load_dataset_row`` re-reads the
        # raw file when an experiment runs and cannot recover the target otherwise.
        "meta": {
            "target_column": target,
            "target_source": target_source,
            "source": "upload",
            "name": name,
            "n_rows": int(profile.n_rows),
            "n_features": int(profile.n_features),
        },
    }
    if existing is not None:
        existing.name = name
        existing.n_rows = profile.n_rows
        existing.n_features = profile.n_features
        existing.profile_json = profile_json
        repo.session.commit()
        row = existing
    else:
        row = repo.create_dataset(
            name=name,
            source="upload",
            n_rows=profile.n_rows,
            n_features=profile.n_features,
            profile_json=profile_json,
            file_hash=digest,
        )
    return DatasetUploadResponse(
        id=row.id,
        name=row.name,
        profile=profile_json,
        warnings=profile.warnings,
        target=target,
        target_source=target_source,
    )
