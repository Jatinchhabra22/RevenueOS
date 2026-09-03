"""Dataset inventory and upload handling."""

from __future__ import annotations

import io
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from app.core.errors import APIError
from app.schemas.api import DatasetSummary
from app.services.data.aliases import canonical_table_name
from app.services.data.loaders import SUPPORTED_SUFFIXES, IngestionError, load_directory
from app.services.runtime import AppRuntime

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_SKIP_SUFFIXES = {".json", ".md", ".txt"}
_ZIP_SUFFIX = ".zip"


def _status_counts(events: pd.DataFrame) -> tuple[int, int]:
    if events.empty or "event_status" not in events.columns:
        return 0, 0
    status = events["event_status"].astype(str).str.lower()
    open_count = int(status.eq("open").sum())
    recovered_count = int(status.isin({"recovered", "resolved"}).sum())
    return open_count, recovered_count


def build_summary(runtime: AppRuntime) -> DatasetSummary:
    loaded = runtime.load_dataset()
    tables = loaded["tables"]
    report = loaded["report"]
    events = tables.get("revenue_events", pd.DataFrame())
    open_count, recovered_count = _status_counts(events)
    ok = bool(report.get("ok", False))
    return DatasetSummary(
        dataset_id=runtime.dataset_id(),
        source=runtime.dataset_source(),
        customer_count=int(len(tables.get("customers", []))),
        transaction_count=int(len(tables.get("transactions", []))),
        subscription_count=int(len(tables.get("subscriptions", []))),
        revenue_event_count=int(len(events)),
        intervention_count=int(len(tables.get("intervention_history", []))),
        open_event_count=open_count,
        recovered_event_count=recovered_count,
        validation_status="ok" if ok else "failed",
        validation_errors=list(report.get("errors") or []),
        validation_warnings=list(report.get("warnings") or []),
    )


def _basename(name: str | None) -> str:
    return Path(str(name or "").replace("\\", "/")).name


def _safe_table_filename(name: str | None) -> str | None:
    raw = _basename(name)
    if not raw or raw.startswith(".") or raw in {".."}:
        return None
    cleaned = _SAFE_NAME.sub("_", raw)
    suffix = Path(cleaned).suffix.lower()
    if suffix in _SKIP_SUFFIXES:
        return None
    if suffix == _ZIP_SUFFIX:
        return cleaned
    if suffix not in SUPPORTED_SUFFIXES:
        raise APIError(
            "UNSUPPORTED_FILE_TYPE",
            f"Unsupported file type '{suffix or 'unknown'}'. Use CSV, XLSX, or a .zip of those files.",
            status_code=415,
        )
    table = canonical_table_name(cleaned)
    if table is None:
        return None
    return f"{table}{suffix}"


def _write_bytes(destination: Path, payload: bytes, limit: int) -> None:
    if len(payload) > limit:
        raise APIError(
            "INVALID_REQUEST",
            f"{destination.name} exceeds the upload size limit.",
            status_code=413,
        )
    if not payload:
        raise APIError("INVALID_REQUEST", f"{destination.name} is empty.", status_code=400)
    destination.write_bytes(payload)


def _extract_zip(payload: bytes, target: Path, limit: int) -> int:
    written = 0
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise APIError("INVALID_REQUEST", "The zip file could not be read.", status_code=400) from exc
    for info in archive.infolist():
        if info.is_dir():
            continue
        filename = _safe_table_filename(info.filename)
        if not filename or Path(filename).suffix.lower() == _ZIP_SUFFIX:
            continue
        data = archive.read(info)
        _write_bytes(target / filename, data, limit)
        written += 1
    return written


def save_uploads(runtime: AppRuntime, files: list[UploadFile]) -> DatasetSummary:
    if not files:
        raise APIError("INVALID_REQUEST", "At least one CSV, XLSX, or ZIP file is required.", status_code=400)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    dataset_id = f"{stamp}_{uuid.uuid4().hex[:8]}"
    target = runtime.uploads_dir / dataset_id
    target.mkdir(parents=True, exist_ok=False)
    try:
        stored = 0
        for upload in files:
            original = _basename(upload.filename)
            payload = upload.file.read()
            if original.lower().endswith(_ZIP_SUFFIX):
                if len(payload) > runtime.upload_max_bytes:
                    raise APIError(
                        "INVALID_REQUEST",
                        f"{original} exceeds the upload size limit.",
                        status_code=413,
                    )
                stored += _extract_zip(payload, target, runtime.upload_max_bytes)
                continue
            filename = _safe_table_filename(upload.filename)
            if filename is None:
                continue
            _write_bytes(target / filename, payload, runtime.upload_max_bytes)
            stored += 1
        if stored == 0:
            raise APIError(
                "INVALID_REQUEST",
                "No merchant tables were found. Upload customers, transactions, subscriptions, "
                "revenue_events, and intervention_history as CSV/XLSX, pick the whole pack folder, "
                "or upload a zip of that folder.",
                status_code=400,
            )
        try:
            loaded = load_directory(target)
        except IngestionError as exc:
            message = str(exc)
            code = "UNSUPPORTED_FILE_TYPE" if "Unsupported format" in message else "VALIDATION_FAILURE"
            status = 415 if code == "UNSUPPORTED_FILE_TYPE" else 422
            raise APIError(code, message, status_code=status) from exc
        report = loaded["report"]
        if not report.get("ok", False):
            errors = "; ".join(report.get("errors") or ["dataset failed validation"])
            raise APIError("VALIDATION_FAILURE", errors, status_code=422)
        runtime.set_active_dataset(target)
        return build_summary(runtime)
    except APIError:
        shutil.rmtree(target, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(target, ignore_errors=True)
        raise APIError("INTERNAL_ERROR", "Failed to store the uploaded dataset.", status_code=500) from exc
