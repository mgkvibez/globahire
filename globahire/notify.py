"""Where an alert goes.

Every notifier takes an injectable transport, so tests assert the exact payload
without opening a socket or needing a bot token.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable, Dict, List, Optional

from .job import Match

Transport = Callable[[str, bytes], None]


def _http_post(url: str, body: bytes) -> None:
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "globahire/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


class Notifier:
    name = "base"

    def send(self, matches: List[Match]) -> None:      # pragma: no cover - interface
        raise NotImplementedError


class TerminalNotifier(Notifier):
    name = "terminal"

    def __init__(self, sink: Optional[Callable[[str], None]] = None):
        self._sink = sink or print

    def send(self, matches: List[Match]) -> None:
        for match in matches:
            self._sink(f"NEW  {match.line()}")
            if match.job.url:
                self._sink(f"     {match.job.url}")


class WebhookNotifier(Notifier):
    """Posts {"text": ...}: Slack, Discord and Mattermost all accept that shape."""

    name = "webhook"

    def __init__(self, url: str, transport: Transport = _http_post):
        self.url = url
        self._transport = transport

    def send(self, matches: List[Match]) -> None:
        text = "\n".join(f"{m.job.title} @ {m.job.company} - {m.job.url}" for m in matches)
        self._transport(self.url, json.dumps({"text": text}).encode("utf-8"))


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, token: str, chat_id: str, transport: Transport = _http_post):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self._transport = transport

    def send(self, matches: List[Match]) -> None:
        for match in matches:
            body = json.dumps({"chat_id": self.chat_id, "disable_web_page_preview": True,
                               "text": f"{match.job.title} @ {match.job.company}\n{match.job.url}"})
            self._transport(self.url, body.encode("utf-8"))


def build(spec: str, env: Optional[Dict[str, str]] = None,
          transport: Transport = _http_post) -> List[Notifier]:
    """Turn "terminal,telegram" into notifiers, using env for the secrets."""
    env = env if env is not None else dict(os.environ)
    out: List[Notifier] = []
    for name in [part.strip().lower() for part in spec.split(",") if part.strip()]:
        if name == "terminal":
            out.append(TerminalNotifier())
        elif name == "webhook":
            url = env.get("GLOBAHIRE_WEBHOOK_URL", "")
            if not url:
                raise ValueError("webhook notifier needs GLOBAHIRE_WEBHOOK_URL")
            out.append(WebhookNotifier(url, transport=transport))
        elif name == "telegram":
            token = env.get("GLOBAHIRE_TELEGRAM_BOT_TOKEN", "")
            chat = env.get("GLOBAHIRE_TELEGRAM_CHAT_ID", "")
            if not token or not chat:
                raise ValueError("telegram notifier needs GLOBAHIRE_TELEGRAM_BOT_TOKEN and GLOBAHIRE_TELEGRAM_CHAT_ID")
            out.append(TelegramNotifier(token, chat, transport=transport))
        else:
            raise ValueError(f"unknown notifier {name!r}; known: terminal, webhook, telegram")
    return out
