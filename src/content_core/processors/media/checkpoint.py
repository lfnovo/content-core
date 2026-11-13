"""Opt-in, private on-disk checkpoints for explicitly resumed transcription."""

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from content_core.common.exceptions import ConfigurationError, FileOperationError


def file_digest(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class AudioCheckpoint:
    """One input/config identity; SQLite lock prevents concurrent paid replays.

    Only successful text is committed. A crashed/uncertain request is retried
    only when the caller explicitly runs extraction again. The OS releases the
    SQLite lock after a process crash; no stale lock-file removal is necessary.
    """

    def __init__(self, directory: str, source: str, identity: dict):
        digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, default=str).encode()
        )
        digest.update(file_digest(source).encode())
        self.directory = Path(directory) / digest.hexdigest()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.lock = sqlite3.connect(self.directory / "lock.sqlite3", timeout=0)
        try:
            self.lock.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError:
            self.lock.close()
            raise ConfigurationError(
                "This audio transcription is already running. Wait before retrying."
            ) from None

    def close(self):
        self.lock.close()

    def read(self, index: int, path: str):
        key = f"{index:08d}-{file_digest(path)}"
        target = self.directory / f"{key}.json"
        if not target.exists():
            return key, None
        try:
            value = json.loads(target.read_text())
            if not isinstance(value, str):
                raise ValueError()
            return key, value
        except (ValueError, OSError):
            raise FileOperationError(
                "Audio checkpoint is unreadable; restore it before retrying to avoid duplicate billing."
            ) from None

    def save(self, key: str, text: str):
        try:
            self._save(key, text)
        except OSError:
            # The provider may already have billed this successful response.
            # Surface a permanent media error, not a retryable worker OSError.
            raise FileOperationError(
                "Could not save an audio checkpoint. Check disk space and permissions before retrying; the chunk may already be billed."
            ) from None

    def _save(self, key: str, text: str):
        # mkstemp is mode 0600; replace prevents a crash exposing partial JSON.
        fd, temporary = tempfile.mkstemp(dir=self.directory)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(text, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.directory / f"{key}.json")
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
