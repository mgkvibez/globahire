"""One pass, or a loop, over the boards a profile cares about."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .job import Job, Match, evaluate
from .profile import Profile
from .sources import SOURCES, collect, detect_source, fetch_json
from .store import SeenStore


def jobs_from_fixture(path: str | Path) -> List[Job]:
    """Replay a saved payload, for tests and for `check --from-fixture`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    name = detect_source(payload)
    if not name:
        raise ValueError(f"{path}: cannot tell which board this payload came from")
    return SOURCES[name].parser(payload)


def run_once(profile: Profile, sources: List[str], store: SeenStore,
             notifiers: Optional[List[Any]] = None, fetcher: Callable[[str], Any] = fetch_json,
             boards: Optional[Dict[str, str]] = None, query: str = "",
             fixture: Optional[str] = None) -> List[Match]:
    """Gather, filter, dedupe, notify. Returns only genuinely new matches."""
    jobs = jobs_from_fixture(fixture) if fixture else collect(sources, boards=boards, fetcher=fetcher, query=query)
    fresh: List[Match] = []
    for job in jobs:
        match = evaluate(job, profile)
        if match is None or not store.is_new(job.key):
            continue
        store.add(job.key)
        fresh.append(match)
    fresh.sort(key=lambda m: -m.score)
    if fresh:
        for notifier in notifiers or []:
            notifier.send(fresh)
    store.save()
    return fresh


def watch_loop(profile: Profile, sources: List[str], store: SeenStore,
               notifiers: Optional[List[Any]] = None, interval_minutes: int = 30,
               cycles: Optional[int] = None, sleep: Callable[[float], None] = time.sleep,
               fetcher: Callable[[str], Any] = fetch_json, boards: Optional[Dict[str, str]] = None,
               on_cycle: Optional[Callable[[int, List[Match]], None]] = None,
               fixture: Optional[str] = None) -> int:
    """Poll forever unless `cycles` is given (used by tests). Returns cycles run."""
    done = 0
    while cycles is None or done < cycles:
        done += 1
        try:
            found = run_once(profile, sources, store, notifiers, fetcher=fetcher, boards=boards,
                             fixture=fixture)
        except Exception as exc:                      # one bad cycle must not kill the radar
            found = []
            if on_cycle:
                on_cycle(done, [])
            print(f"cycle {done}: {exc}")
        else:
            if on_cycle:
                on_cycle(done, found)
        if cycles is None or done < cycles:
            sleep(interval_minutes * 60)
    return done
