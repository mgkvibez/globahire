"""Load the thing that decides what counts as a match.

profile.yaml is read by a deliberately small parser: top-level keys, scalars,
inline lists and block lists. It refuses what it does not understand instead of
silently dropping a filter, because a dropped filter means missed jobs.
JSON is accepted too when the file ends in .json.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


class ProfileError(ValueError):
    """Raised when a profile cannot be read unambiguously."""


@dataclass
class Profile:
    stack: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    remote: bool = False
    locations: List[str] = field(default_factory=list)
    min_match: int = 1
    experience: str = ""

    def describe(self) -> str:
        bits = [f"stack: {', '.join(self.stack) or '-'}"]
        if self.roles:
            bits.append(f"roles: {', '.join(self.roles)}")
        bits.append("remote only" if self.remote else "remote or onsite")
        if self.exclude:
            bits.append(f"excluding: {', '.join(self.exclude)}")
        return "; ".join(bits)


def _scalar(value: str) -> Any:
    v = value.strip()
    if not v:
        return ""
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v.strip("'\"")


def parse_yaml_subset(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current: str = ""
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s*-\s+", line):                      # block list item
            if not current:
                raise ProfileError(f"line {lineno}: list item without a key")
            item = _scalar(re.sub(r"^\s*-\s+", "", line))
            if data.get(current) is None:
                data[current] = []
            bucket = data[current]
            if not isinstance(bucket, list):
                raise ProfileError(f"line {lineno}: {current!r} is a scalar, not a list")
            bucket.append(item)
            continue
        if re.match(r"^[A-Za-z_][\w-]*\s*:", line):           # key: value
            key, _, rest = line.partition(":")
            current = key.strip()
            data[current] = _scalar(rest) if rest.strip() else None
            continue
        raise ProfileError(f"line {lineno}: cannot parse {raw!r}")
    return data


def load(path: str | Path) -> Profile:
    p = Path(path)
    if not p.exists():
        raise ProfileError(f"profile not found: {p}")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProfileError(f"{p}: invalid JSON ({exc})") from exc
    else:
        data = parse_yaml_subset(text)

    def as_list(name: str) -> List[str]:
        value = data.get(name) or []
        if isinstance(value, str):
            return [x.strip().lower() for x in value.split(",") if x.strip()]
        if isinstance(value, list):
            return [str(x).strip().lower() for x in value if str(x).strip()]
        raise ProfileError(f"{p}: {name!r} must be a list")

    profile = Profile(
        stack=as_list("stack"),
        roles=as_list("roles"),
        exclude=as_list("exclude"),
        remote=bool(data.get("remote", False)),
        locations=as_list("locations"),
        min_match=int(data.get("min_match", 1) or 1),
        experience=str(data.get("experience", "")),
    )
    if not profile.stack and not profile.roles:
        raise ProfileError(f"{p}: needs at least one of 'stack' or 'roles'")
    return profile
