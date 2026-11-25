"""Private content-addressed storage for normalized exercise images."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import tempfile
from pathlib import Path

from app.domain.ingestion.images import AdmittedJpeg

_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class PrivateMediaStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def store(self, image: AdmittedJpeg) -> None:
        self._validate_digest(image.sha256)
        if not hmac.compare_digest(hashlib.sha256(image.content).hexdigest(), image.sha256):
            raise ValueError("Media SHA-256 does not match its content")

        directory = self._root / image.sha256[:2]
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._root, 0o700)
        os.chmod(directory, 0o700)
        destination = directory / f"{image.sha256}.jpg"
        if destination.exists():
            existing = destination.read_bytes()
            if not hmac.compare_digest(hashlib.sha256(existing).hexdigest(), image.sha256):
                raise OSError("Stored media failed integrity validation")
            os.chmod(destination, 0o600)
            return

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=directory,
                prefix=".media-",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                os.fchmod(temporary.fileno(), 0o600)
                temporary.write(image.content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, destination)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def read(self, media_sha: str) -> bytes:
        self._validate_digest(media_sha)
        path = self._path_for(media_sha)
        if path.stat().st_size > 8 * 1024 * 1024:
            raise OSError("Stored media exceeds the configured size limit")
        content = path.read_bytes()
        if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), media_sha):
            raise OSError("Stored media failed integrity validation")
        return content

    def delete(self, media_sha: str) -> bool:
        self._validate_digest(media_sha)
        path = self._path_for(media_sha)
        if not path.exists():
            return False
        path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass
        return True

    def _path_for(self, media_sha: str) -> Path:
        return self._root / media_sha[:2] / f"{media_sha}.jpg"

    @staticmethod
    def _validate_digest(media_sha: str) -> None:
        if not isinstance(media_sha, str) or not _SHA256_PATTERN.fullmatch(media_sha):
            raise ValueError("Media SHA-256 must contain 64 lowercase hexadecimal characters")
