import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from globahire import notify
from globahire.job import Job, Match

M = [Match(job=Job(title="Backend Engineer", company="Acme", url="https://x/1", source="remotive"), score=7, reasons=["stack:python"])]

def test_terminal_notifier_writes_lines():
    out = []
    notify.TerminalNotifier(sink=out.append).send(M)
    assert any("Backend Engineer" in line for line in out)
    assert any("https://x/1" in line for line in out)

def test_webhook_payload_shape():
    sent = []
    notify.WebhookNotifier("https://hooks/x", transport=lambda u, b: sent.append((u, json.loads(b)))).send(M)
    assert sent[0][0] == "https://hooks/x" and "Backend Engineer" in sent[0][1]["text"]

def test_telegram_posts_one_message_per_match_with_chat_id():
    sent = []
    notify.TelegramNotifier("TOKEN", "42", transport=lambda u, b: sent.append((u, json.loads(b)))).send(M)
    assert sent[0][0].endswith("/botTOKEN/sendMessage") and sent[0][1]["chat_id"] == "42"

def test_build_from_spec_and_env():
    env = {"GLOBAHIRE_TELEGRAM_BOT_TOKEN": "T", "GLOBAHIRE_TELEGRAM_CHAT_ID": "9"}
    built = notify.build("terminal,telegram", env=env, transport=lambda u, b: None)
    assert [n.name for n in built] == ["terminal", "telegram"]

def test_missing_credentials_fail_loudly_not_silently():
    with pytest.raises(ValueError):
        notify.build("telegram", env={}, transport=lambda u, b: None)
    with pytest.raises(ValueError):
        notify.build("carrier-pigeon", env={}, transport=lambda u, b: None)
