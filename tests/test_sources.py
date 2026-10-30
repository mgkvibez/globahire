import pathlib, sys, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from globahire import sources

FIX = pathlib.Path(__file__).parent / "fixtures"

def load(name): return json.loads((FIX / name).read_text())

def test_remotive_parser_detects_remote_and_tags():
    jobs = sources.parse_remotive(load("remotive.json"))
    assert len(jobs) == 3 and jobs[0].remote is True and jobs[0].company == "Acme Remote"
    assert "fastapi" in jobs[0].tags

def test_arbeitnow_parser_reads_remote_flag():
    jobs = sources.parse_arbeitnow(load("arbeitnow.json"))
    assert len(jobs) == 2 and jobs[0].remote is False and jobs[1].remote is True

def test_greenhouse_parser_flattens_location_object():
    jobs = sources.parse_greenhouse(load("greenhouse.json"), company="Acme")
    assert jobs[0].location == "Remote - EU" and jobs[0].remote is True and jobs[0].company == "Acme"

def test_lever_parser_reads_categories():
    jobs = sources.parse_lever(load("lever.json"))
    assert jobs[0].title == "Senior Backend Engineer" and jobs[0].remote is True

def test_detect_source_identifies_each_fixture():
    assert sources.detect_source(load("remotive.json")) == "remotive"
    assert sources.detect_source(load("arbeitnow.json")) == "arbeitnow"
    assert sources.detect_source(load("greenhouse.json")) == "greenhouse"
    assert sources.detect_source(load("lever.json")) == "lever"
    assert sources.detect_source({"nope": 1}) is None

def test_collect_uses_injected_fetcher_and_never_the_network():
    def fake(url):
        return load("remotive.json")
    jobs = sources.collect(["remotive"], fetcher=fake)
    assert len(jobs) == 3

def test_unknown_source_and_missing_board_token_are_clear_errors():
    with pytest.raises(sources.FetchError):
        sources.collect(["monster"], fetcher=lambda u: {})
    with pytest.raises(sources.FetchError):
        sources.collect(["greenhouse"], fetcher=lambda u: {"jobs": []})

def test_a_dead_source_raises_fetch_error_with_url():
    def boom(url): raise sources.FetchError(f"{url}: 503")
    with pytest.raises(sources.FetchError):
        sources.collect(["remotive"], fetcher=boom)
