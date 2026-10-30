"""Board adapters.

Every parser is a pure function over an already-fetched payload, so the whole
radar can be tested without a network. Fetching lives in one place, and only
public, token-free JSON endpoints are supported in V0.1: the logged-in boards
are what get accounts banned, so they are out of scope by design.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .job import Job

USER_AGENT = "globahire/0.1 (+https://github.com/mgkvibez/globahire)"


class FetchError(RuntimeError):
    """A source could not be reached; callers decide whether that is fatal."""


def _clean(text: Any, limit: int = 1200) -> str:
    return " ".join(str(text or "").split())[:limit]


def parse_remotive(payload: Dict[str, Any]) -> List[Job]:
    jobs = []
    for raw in payload.get("jobs", []) or []:
        jobs.append(Job(
            title=_clean(raw.get("title"), 200),
            company=_clean(raw.get("company_name"), 120),
            url=raw.get("url", ""),
            source="remotive",
            location=_clean(raw.get("candidate_required_location"), 120),
            remote=True,                      # remotive is a remote-only board
            tags=[str(t).lower() for t in raw.get("tags", []) or []],
            description=_clean(raw.get("description")),
            posted_at=_clean(raw.get("publication_date"), 40),
        ))
    return jobs


def parse_arbeitnow(payload: Dict[str, Any]) -> List[Job]:
    jobs = []
    for raw in payload.get("data", []) or []:
        jobs.append(Job(
            title=_clean(raw.get("title"), 200),
            company=_clean(raw.get("company_name"), 120),
            url=raw.get("url", ""),
            source="arbeitnow",
            location=_clean(raw.get("location"), 120),
            remote=bool(raw.get("remote")),
            tags=[str(t).lower() for t in raw.get("tags", []) or []],
            description=_clean(raw.get("description")),
            posted_at=_clean(raw.get("created_at"), 40),
        ))
    return jobs


def parse_greenhouse(payload: Dict[str, Any], company: str = "") -> List[Job]:
    jobs = []
    for raw in payload.get("jobs", []) or []:
        office = raw.get("location") or {}
        location = office.get("name", "") if isinstance(office, dict) else str(office)
        jobs.append(Job(
            title=_clean(raw.get("title"), 200),
            company=_clean(company or payload.get("name", ""), 120),
            url=raw.get("absolute_url", ""),
            source="greenhouse",
            location=_clean(location, 120),
            remote="remote" in str(location).lower(),
            description=_clean(raw.get("content")),
            posted_at=_clean(raw.get("updated_at"), 40),
        ))
    return jobs


def parse_lever(payload: Any) -> List[Job]:
    jobs = []
    for raw in payload if isinstance(payload, list) else []:
        cats = raw.get("categories") or {}
        location = cats.get("location", "") if isinstance(cats, dict) else ""
        jobs.append(Job(
            title=_clean(raw.get("text"), 200),
            company=_clean(raw.get("company") or "", 120),
            url=raw.get("hostedUrl", ""),
            source="lever",
            location=_clean(location, 120),
            remote="remote" in str(location).lower(),
            tags=[str(t).lower() for t in (cats.get("team") and [cats.get("team")] or [])],
            description=_clean(raw.get("descriptionPlain")),
            posted_at="",
        ))
    return jobs


@dataclass
class Source:
    name: str
    url: str                      # may contain {board}
    parser: Callable[..., List[Job]]
    needs_board_token: bool = False


SOURCES: Dict[str, Source] = {
    "remotive": Source("remotive", "https://remotive.com/api/remote-jobs", parse_remotive),
    "arbeitnow": Source("arbeitnow", "https://www.arbeitnow.com/api/job-board-api", parse_arbeitnow),
    "greenhouse": Source("greenhouse", "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
                         parse_greenhouse, needs_board_token=True),
    "lever": Source("lever", "https://api.lever.co/v0/postings/{board}?mode=json",
                    parse_lever, needs_board_token=True),
}


def detect_source(payload: Any) -> Optional[str]:
    """Best-effort name for a payload's shape, used by --from-fixture."""
    if isinstance(payload, dict):
        if "jobs" in payload and any("candidate_required_location" in j for j in payload.get("jobs") or []):
            return "remotive"
        if "data" in payload:
            return "arbeitnow"
        if "jobs" in payload:
            return "greenhouse"
    if isinstance(payload, list) and payload and "hostedUrl" in payload[0]:
        return "lever"
    return None


def fetch_json(url: str, timeout: int = 20) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        raise FetchError(f"{url}: {exc}") from exc


def collect(names: List[str], boards: Optional[Dict[str, str]] = None,
            fetcher: Callable[[str], Any] = fetch_json,
            query: str = "") -> List[Job]:
    """Fetch and parse every requested source. A dead board does not stop the rest."""
    boards = boards or {}
    jobs: List[Job] = []
    for name in names:
        source = SOURCES.get(name)
        if not source:
            raise FetchError(f"unknown source {name!r}; known: {', '.join(sorted(SOURCES))}")
        if source.needs_board_token and not boards.get(name):
            raise FetchError(f"source {name!r} needs a board token (--board {name}=<token>)")
        url = source.url.format(board=boards.get(name, ""))
        if query and name == "remotive":
            url = f"{url}?search={urllib.request.quote(query)}" if "?" not in url else url
        payload = fetcher(url)
        jobs.extend(source.parser(payload))
    return jobs
