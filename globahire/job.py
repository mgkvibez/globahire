"""A normalised job, and the only place that decides what counts as a match."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List

from .profile import Profile


@dataclass
class Job:
    title: str
    company: str
    url: str
    source: str
    location: str = ""
    remote: bool = False
    tags: List[str] = field(default_factory=list)
    description: str = ""
    posted_at: str = ""

    @property
    def key(self) -> str:
        """Stable identity across boards and reposts of the same role."""
        basis = re.sub(r"\s+", " ", f"{self.company}|{self.title}|{self.location}".lower()).strip()
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    def haystack(self) -> str:
        return " ".join([self.title, self.location, " ".join(self.tags), self.description]).lower()


@dataclass
class Match:
    job: Job
    score: int
    reasons: List[str]

    def line(self) -> str:
        where = self.job.location or ("remote" if self.job.remote else "location unknown")
        return f"{self.job.title} @ {self.job.company} ({where}) [{self.job.source}] score={self.score}"


def evaluate(job: Job, profile: Profile) -> Match | None:
    """Return a Match, or None when the job is filtered out.

    Filters run before scoring: a required-remote profile drops onsite roles,
    exclusions drop anything mentioning them, and a location list keeps only
    jobs whose location contains one of the allowed strings.
    """
    text = job.haystack()
    if profile.remote and not job.remote:
        return None
    for bad in profile.exclude:
        if bad and re.search(rf"\b{re.escape(bad)}\b", text):
            return None
    if profile.locations and not any(loc in (job.location or "").lower() for loc in profile.locations):
        if not (profile.remote and job.remote):
            return None

    score = 0
    reasons: List[str] = []
    for skill in profile.stack:
        if re.search(rf"\b{re.escape(skill)}\b", text):
            score += 2
            reasons.append(f"stack:{skill}")
    for role in profile.roles:
        if re.search(rf"\b{re.escape(role)}\b", text):
            score += 3
            reasons.append(f"role:{role}")
    if score < max(profile.min_match, 1):
        return None
    return Match(job=job, score=score, reasons=reasons)
