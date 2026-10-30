import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from globahire.job import Job, evaluate
from globahire.profile import Profile

def job(**kw):
    base = dict(title="Backend Engineer", company="Acme", url="u", source="remotive", location="Worldwide",
                remote=True, tags=["python"], description="")
    base.update(kw); return Job(**base)

def test_stack_and_role_scores():
    m = evaluate(job(tags=["python", "fastapi"]), Profile(stack=["python", "fastapi"], roles=["backend"], remote=True))
    assert m and m.score == 7 and "stack:python" in m.reasons and "role:backend" in m.reasons

def test_remote_requirement_filters_onsite():
    assert evaluate(job(remote=False, location="Berlin"), Profile(stack=["python"], remote=True)) is None

def test_exclusion_wins_over_score():
    p = Profile(stack=["python"], roles=["backend"], exclude=["unpaid"])
    assert evaluate(job(description="Unpaid internship, backend python"), p) is None

def test_min_match_threshold():
    assert evaluate(job(tags=[], description="nothing relevant"), Profile(stack=["python"], min_match=1)) is None

def test_key_is_stable_across_boards_but_not_across_roles():
    a = job(source="remotive"); b = job(source="arbeitnow")
    assert a.key == b.key
    assert a.key != job(title="Frontend Engineer").key
