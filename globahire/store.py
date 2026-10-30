"""Remember what has already been announced, so a radar does not repeat itself."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import List, Set


class SeenStore:
    def __init__(self, path: str | Path = ".globahire/seen.json"):
        self.path = Path(path)
        self._keys: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return                      # a corrupt store must not stop the radar
        self._keys = set(data.get("seen", []))

    def is_new(self, key: str) -> bool:
        return key not in self._keys

    def add(self, key: str) -> None:
        self._keys.add(key)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"seen": sorted(self._keys)}, indent=2)
        handle, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, self.path)
        except OSError:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def __len__(self) -> int:
        return len(self._keys)
