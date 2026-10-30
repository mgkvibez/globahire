"""globahire command line.

Exit codes are a contract: 0 nothing new, 3 new matches found, 2 an error the
user must fix (bad profile, unknown source, missing credential).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from . import notify, profile as profile_mod
from .sources import SOURCES, FetchError
from .store import SeenStore
from .watch import run_once, watch_loop

EXIT_CLEAN = 0
EXIT_ERROR = 2
EXIT_MATCHES = 3

EXAMPLE_PROFILE = """# globahire profile
# stack entries are matched as whole words; roles weigh more than stack tags.
stack:
  - python
  - fastapi
  - postgres

roles:
  - backend
  - platform

# required: only remote roles will be announced
remote: true

# optional: drop anything mentioning these
exclude:
  - unpaid
  - internship

# optional: keep only these locations (ignored for remote roles when remote: true)
# locations:
#   - nigeria
#   - europe

# optional: how many points a job needs to count (stack=2, role=3)
min_match: 2
"""


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="globahire",
                                description="A personal job radar. Alerts only: it never applies for you.")
    p.add_argument("--version", action="version", version=f"globahire {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="write a starter profile.yaml")
    init.add_argument("--path", default="profile.yaml")
    init.add_argument("--force", action="store_true")

    for name, help_text in (("check", "one pass over the boards and report"),
                            ("watch", "keep checking on an interval")):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("--profile", default="profile.yaml")
        s.add_argument("--sources", default="remotive,arbeitnow",
                       help="comma separated: " + ", ".join(sorted(SOURCES)))
        s.add_argument("--board", action="append", default=[],
                       help="board token for greenhouse/lever, e.g. --board greenhouse=acme")
        s.add_argument("--state", default=".globahire/seen.json")
        s.add_argument("--notify", default="terminal", help="terminal, webhook, telegram")
        s.add_argument("--query", default="", help="optional keyword for boards that support search")
        s.add_argument("--json", action="store_true")
        s.add_argument("--from-fixture", default=None,
                       help="replay a saved payload instead of fetching (offline use)")
        if name == "watch":
            s.add_argument("--interval", type=int, default=30, help="minutes between passes")
            s.add_argument("--cycles", type=int, default=None, help="stop after N passes (default: forever)")

    sub.add_parser("sources", help="list supported boards")
    return p


def _boards(pairs: List[str]) -> dict:
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"--board expects name=token, got {pair!r}")
        name, _, token = pair.partition("=")
        out[name.strip()] = token.strip()
    return out


def _emit(matches, as_json: bool, already_notified: bool = False) -> None:
    if already_notified and not as_json:
        return                      # the notifier already printed them
    if as_json:
        print(json.dumps([{"title": m.job.title, "company": m.job.company, "url": m.job.url,
                           "source": m.job.source, "location": m.job.location,
                           "score": m.score, "reasons": m.reasons} for m in matches], indent=2))
    else:
        print(f"{len(matches)} new match(es)")
        for match in matches:
            print(f"  {match.line()}")
            if match.job.url:
                print(f"    {match.job.url}")


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)

    if args.cmd == "sources":
        for name, source in sorted(SOURCES.items()):
            needs = "  (needs --board token)" if source.needs_board_token else ""
            print(f"{name:12} {source.url}{needs}")
        return EXIT_CLEAN

    if args.cmd == "init":
        import pathlib
        target = pathlib.Path(args.path)
        if target.exists() and not args.force:
            print(f"{target} already exists; pass --force to overwrite", file=sys.stderr)
            return EXIT_ERROR
        target.write_text(EXAMPLE_PROFILE, encoding="utf-8")
        print(f"wrote {target}; edit it, then: globahire check")
        return EXIT_CLEAN

    try:
        prof = profile_mod.load(args.profile)
    except profile_mod.ProfileError as exc:
        print(f"profile error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    try:
        notifiers = notify.build(args.notify) if args.notify else []
    except ValueError as exc:
        print(f"notifier error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    try:
        boards = _boards(args.board)
    except ValueError as exc:
        print(f"argument error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    store = SeenStore(args.state)

    if args.cmd == "check":
        try:
            matches = run_once(prof, sources, store, notifiers, boards=boards,
                               query=args.query, fixture=args.from_fixture)
        except (FetchError, ValueError) as exc:
            print(f"fetch error: {exc}", file=sys.stderr)
            return EXIT_ERROR
        _emit(matches, args.json, already_notified=bool(notifiers))
        return EXIT_MATCHES if matches else EXIT_CLEAN

    # watch
    def on_cycle(index: int, matches) -> None:
        print(f"cycle {index}: {len(matches)} new")

    try:
        watch_loop(prof, sources, store, notifiers, interval_minutes=args.interval,
                   cycles=args.cycles, boards=boards, on_cycle=on_cycle,
                   fixture=args.from_fixture)
    except KeyboardInterrupt:
        print("stopped")
    return EXIT_CLEAN


if __name__ == "__main__":                                    # pragma: no cover
    sys.exit(main())
