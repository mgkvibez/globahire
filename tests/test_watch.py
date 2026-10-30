import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from globahire.profile import Profile
from globahire.store import SeenStore
from globahire.watch import run_once, watch_loop, jobs_from_fixture

FIX = pathlib.Path(__file__).parent / "fixtures"
PROFILE = Profile(stack=["python", "fastapi", "postgres"], roles=["backend"], remote=True, exclude=["unpaid"], min_match=2)

class Collector:
    def __init__(self): self.batches = []
    def send(self, matches): self.batches.append([m.job.title for m in matches])

def test_fixture_replay_matches_only_the_good_job(tmp_path):
    matches = run_once(PROFILE, ["remotive"], SeenStore(tmp_path / "x1.json"),
                       fixture=str(FIX / "remotive.json"))
    titles = [m.job.title for m in matches]
    assert titles == ["Backend Engineer (Python)"]        # unpaid and react roles filtered out

def test_second_pass_is_silent_because_keys_are_remembered(tmp_path):
    store = SeenStore(tmp_path / "seen.json")
    first = run_once(PROFILE, ["remotive"], store, fixture=str(FIX / "remotive.json"))
    second = run_once(PROFILE, ["remotive"], store, fixture=str(FIX / "remotive.json"))
    assert len(first) == 1 and second == []
    assert len(SeenStore(tmp_path / "seen.json")) == 1

def test_notifier_receives_the_matches_once(tmp_path):
    sink = Collector()
    run_once(PROFILE, ["remotive"], SeenStore(tmp_path / "s.json"), notifiers=[sink], fixture=str(FIX / "remotive.json"))
    run_once(PROFILE, ["remotive"], SeenStore(tmp_path / "s.json"), notifiers=[sink], fixture=str(FIX / "remotive.json"))
    assert len(sink.batches) == 1

def test_loop_runs_requested_cycles_and_sleeps_between_them(tmp_path):
    slept = []
    cycles = []
    n = watch_loop(PROFILE, ["remotive"], SeenStore(tmp_path / "s.json"), interval_minutes=5, cycles=3,
                   sleep=lambda s: slept.append(s), fetcher=lambda url: json.loads((FIX / "remotive.json").read_text()),
                   on_cycle=lambda i, m: cycles.append(i))
    assert n == 3 and cycles == [1, 2, 3] and slept == [300, 300]

def test_a_broken_cycle_does_not_kill_the_loop(tmp_path):
    calls = {"n": 0}
    def flaky_fetch(url):
        calls["n"] += 1
        if calls["n"] == 1: raise RuntimeError("board down")
        return json.loads((FIX / "remotive.json").read_text())
    seen = []
    watch_loop(PROFILE, ["remotive"], SeenStore(tmp_path / "s.json"), cycles=2, sleep=lambda s: None,
               fetcher=flaky_fetch, on_cycle=lambda i, m: seen.append((i, len(m))))
    assert seen[0] == (1, 0) and seen[1] == (2, 1)

def test_fixture_with_unknown_shape_is_an_error(tmp_path):
    p = tmp_path / "x.json"; p.write_text('{"nope": 1}')
    try:
        jobs_from_fixture(p)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "cannot tell" in str(exc)
