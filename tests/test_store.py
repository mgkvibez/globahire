import pathlib, sys, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from globahire.store import SeenStore

def test_add_and_reload(tmp_path):
    path = tmp_path / "seen.json"
    s = SeenStore(path); s.add("abc"); s.save()
    assert SeenStore(path).is_new("abc") is False and SeenStore(path).is_new("def") is True

def test_corrupt_store_does_not_crash(tmp_path):
    path = tmp_path / "seen.json"; path.write_text("{not json")
    assert SeenStore(path).is_new("abc") is True

def test_save_is_atomic_and_leaves_no_tmp_files(tmp_path):
    path = tmp_path / "seen.json"
    s = SeenStore(path); s.add("x"); s.save()
    assert [p.name for p in tmp_path.iterdir()] == ["seen.json"]
    assert json.loads(path.read_text())["seen"] == ["x"]
