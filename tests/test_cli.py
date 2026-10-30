import io, json, pathlib, sys, contextlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from globahire.cli import main, EXIT_CLEAN, EXIT_ERROR, EXIT_MATCHES

FIX = pathlib.Path(__file__).parent / "fixtures"
PROFILE = """stack:\n  - python\n  - fastapi\n  - postgres\nroles:\n  - backend\nremote: true\nexclude:\n  - unpaid\nmin_match: 2\n"""

def run(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = main(args)
    return code, buf.getvalue()

def test_init_writes_a_profile_then_refuses_to_clobber(tmp_path):
    p = tmp_path / "profile.yaml"
    code, out = run(["init", "--path", str(p)])
    assert code == EXIT_CLEAN and p.exists() and "globahire check" in out
    code2, out2 = run(["init", "--path", str(p)])
    assert code2 == EXIT_ERROR and "already exists" in out2

def test_check_reports_matches_and_exits_three(tmp_path):
    prof = tmp_path / "p.yaml"; prof.write_text(PROFILE)
    code, out = run(["check", "--profile", str(prof), "--from-fixture", str(FIX / "remotive.json"),
                     "--state", str(tmp_path / "seen.json"), "--notify", "", "--json"])
    assert code == EXIT_MATCHES
    payload = json.loads(out[out.index("["):])
    assert payload[0]["title"] == "Backend Engineer (Python)" and payload[0]["score"] >= 2

def test_check_exits_zero_when_nothing_is_new(tmp_path):
    prof = tmp_path / "p.yaml"; prof.write_text(PROFILE)
    for expected in (EXIT_MATCHES, EXIT_CLEAN):
        code, _ = run(["check", "--profile", str(prof), "--from-fixture", str(FIX / "remotive.json"),
                       "--state", str(tmp_path / "seen.json"), "--notify", ""])
        assert code == expected

def test_bad_profile_and_bad_notifier_are_exit_two(tmp_path):
    bad = tmp_path / "bad.yaml"; bad.write_text("remote: true\n")
    code, out = run(["check", "--profile", str(bad), "--notify", ""])
    assert code == EXIT_ERROR and "profile error" in out
    prof = tmp_path / "p.yaml"; prof.write_text(PROFILE)
    code2, out2 = run(["check", "--profile", str(prof), "--notify", "telegram"])
    assert code2 == EXIT_ERROR and "notifier error" in out2

def test_sources_lists_boards_and_flags_token_requirements():
    code, out = run(["sources"])
    assert code == EXIT_CLEAN and "remotive" in out and "needs --board token" in out

def test_watch_reaches_the_loop_with_cycles(tmp_path):
    prof = tmp_path / "p.yaml"; prof.write_text(PROFILE)
    code, out = run(["watch", "--profile", str(prof), "--from-fixture", str(FIX / "remotive.json"),
                     "--state", str(tmp_path / "s.json"), "--notify", "", "--cycles", "1", "--interval", "0"])
    assert code == EXIT_CLEAN and "cycle 1" in out
