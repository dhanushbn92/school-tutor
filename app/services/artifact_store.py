import os
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class ArtifactStore(Protocol):
    def save(self, *, content_id: int, extension: str, data: bytes) -> str: ...
    def read(self, relative_path: str) -> bytes: ...
    def exists(self, relative_path: str) -> bool: ...


class LocalArtifactStore:
    """Writes artifacts under `settings.artifact_dir`.

    The returned `relative_path` is opaque to callers and is what gets stored
    in `GeneratedContent.artifact_url`. The download route uses `read()` to
    serve bytes; swap this class for `GCSArtifactStore` in prod without
    changing callers.
    """

    def __init__(self, base_dir: str | None = None):
        self._base = Path(base_dir or get_settings().artifact_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, *, content_id: int, extension: str, data: bytes) -> str:
        safe_ext = extension.lstrip(".").lower()
        filename = f"{content_id}.{safe_ext}"
        path = self._base / filename
        path.write_bytes(data)
        return filename

    def read(self, relative_path: str) -> bytes:
        path = self._safe_path(relative_path)
        return path.read_bytes()

    def exists(self, relative_path: str) -> bool:
        try:
            return self._safe_path(relative_path).is_file()
        except ValueError:
            return False

    def _safe_path(self, relative_path: str) -> Path:
        candidate = (self._base / relative_path).resolve()
        base_resolved = self._base.resolve()
        if os.path.commonpath([str(candidate), str(base_resolved)]) != str(base_resolved):
            raise ValueError(f"Refusing to read outside artifact dir: {relative_path}")
        return candidate


class GCSArtifactStore:
    """Stores artifacts in a Google Cloud Storage bucket.

    Cloud Run is stateless — the container's filesystem is ephemeral and not
    shared between instances — so artifacts must live in object storage. The
    contract matches `LocalArtifactStore`: `save()` returns the same opaque
    `<content_id>.<ext>` filename which is persisted in
    `GeneratedContent.artifact_url`. Internally we prefix that with
    `settings.gcs_prefix` so multiple apps can share one bucket without
    colliding.

    Auth uses Application Default Credentials. On Cloud Run that resolves to
    the runtime service account automatically; locally, run
    `gcloud auth application-default login` once.
    """

    def __init__(self, bucket: str | None = None, prefix: str | None = None):
        from google.cloud import storage  # local import: only needed in GCS mode

        s = get_settings()
        bucket_name = bucket or s.gcs_bucket
        if not bucket_name:
            raise RuntimeError(
                "artifact_backend='gcs' requires GCS_BUCKET to be set."
            )
        self._prefix = (prefix if prefix is not None else s.gcs_prefix) or ""
        # Normalise: no leading slash, exactly one trailing slash if non-empty.
        self._prefix = self._prefix.lstrip("/")
        if self._prefix and not self._prefix.endswith("/"):
            self._prefix += "/"
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)

    def _key(self, relative_path: str) -> str:
        # Defensive: callers store the value we returned from save(), but make
        # sure we never accidentally double-prefix or escape upward.
        rel = relative_path.lstrip("/")
        if ".." in rel.split("/"):
            raise ValueError(f"Refusing to access GCS object: {relative_path}")
        return f"{self._prefix}{rel}"

    def save(self, *, content_id: int, extension: str, data: bytes) -> str:
        safe_ext = extension.lstrip(".").lower()
        filename = f"{content_id}.{safe_ext}"
        blob = self._bucket.blob(self._key(filename))
        blob.upload_from_string(data, content_type=_guess_content_type(safe_ext))
        return filename

    def read(self, relative_path: str) -> bytes:
        blob = self._bucket.blob(self._key(relative_path))
        return blob.download_as_bytes()

    def exists(self, relative_path: str) -> bool:
        try:
            return self._bucket.blob(self._key(relative_path)).exists(self._client)
        except ValueError:
            return False


def _guess_content_type(ext: str) -> str:
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "svg": "image/svg+xml",
        "html": "text/html; charset=utf-8",
        "json": "application/json",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }.get(ext, "application/octet-stream")


@lru_cache
def get_artifact_store() -> ArtifactStore:
    """Returns the configured artifact store.

    Selected via `ARTIFACT_BACKEND` env var: "local" (default) or "gcs".
    Cached so we reuse one GCS client per process.
    """
    s = get_settings()
    backend = (s.artifact_backend or "local").lower()
    if backend == "gcs":
        return GCSArtifactStore()
    if backend == "local":
        return LocalArtifactStore()
    raise RuntimeError(f"Unknown ARTIFACT_BACKEND: {s.artifact_backend!r}")
