"""Request-scoped application runtime. Routes depend on this, not on hardcoded paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import Settings, get_settings
from app.core.errors import APIError
from app.services.data.loaders import IngestionError, load_directory


@dataclass
class AppRuntime:
    data_dir: Path
    artifacts_dir: Path
    models_dir: Path
    uploads_dir: Path
    workflows_dir: Path
    active_dataset_dir: Path
    upload_max_bytes: int
    disable_llm: bool = False
    _tables: dict[str, pd.DataFrame] | None = field(default=None, repr=False)
    _report: dict[str, Any] | None = field(default=None, repr=False)
    _source_key: str | None = field(default=None, repr=False)
    _opportunity_cache: dict[str, list] = field(default_factory=dict, repr=False)

    @classmethod
    def from_settings(cls, settings: Settings | None = None, *, disable_llm: bool = False) -> AppRuntime:
        cfg = settings or get_settings()
        active = cfg.active_dataset_path
        return cls(
            data_dir=cfg.data_path,
            artifacts_dir=cfg.artifacts_path,
            models_dir=cfg.models_path,
            uploads_dir=cfg.uploads_path,
            workflows_dir=cfg.workflows_path,
            active_dataset_dir=active,
            upload_max_bytes=cfg.upload_max_bytes,
            disable_llm=disable_llm,
        )

    def dataset_id(self) -> str:
        return self.active_dataset_dir.name

    def dataset_source(self) -> str:
        parent = self.active_dataset_dir.parent.name
        if parent == "uploads":
            return f"upload:{self.active_dataset_dir.name}"
        return self.active_dataset_dir.name

    def _fingerprint(self) -> str:
        if not self.active_dataset_dir.exists():
            return "missing"
        stamps = []
        for path in sorted(self.active_dataset_dir.iterdir()):
            if path.is_file():
                stamps.append(f"{path.name}:{path.stat().st_mtime_ns}:{path.stat().st_size}")
        return "|".join(stamps)

    def invalidate(self) -> None:
        self._tables = None
        self._report = None
        self._source_key = None
        self._opportunity_cache.clear()

    def set_active_dataset(self, directory: Path) -> None:
        self.active_dataset_dir = directory
        self.invalidate()

    def load_dataset(self) -> dict[str, Any]:
        key = str(self.active_dataset_dir) + "::" + self._fingerprint()
        if self._tables is not None and self._source_key == key:
            return {"tables": self._tables, "report": self._report}
        if not self.active_dataset_dir.exists():
            raise APIError(
                "DATASET_NOT_FOUND",
                f"Active dataset directory was not found: {self.active_dataset_dir.name}",
                status_code=404,
            )
        try:
            loaded = load_directory(self.active_dataset_dir)
        except IngestionError as exc:
            raise APIError("DATASET_LOAD_FAILED", str(exc), status_code=422) from exc
        self._tables = loaded["tables"]
        self._report = loaded["report"]
        self._source_key = key
        self._opportunity_cache.clear()
        return loaded

    def tables(self) -> dict[str, pd.DataFrame]:
        return self.load_dataset()["tables"]

    def report(self) -> dict[str, Any]:
        return self.load_dataset()["report"]
