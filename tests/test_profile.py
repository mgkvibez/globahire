import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from globahire import profile as prof

def test_block_lists_and_scalars():
    p = prof.parse_yaml_subset("stack:\n  - python\n  - postgres\nremote: true\nmin_match: 3\n")
    assert p["stack"] == ["python", "postgres"] and p["remote"] is True and p["min_match"] == 3

def test_inline_list_and_comments():
    p = prof.parse_yaml_subset("stack: [python, fastapi]  # main stack\nroles:\n  - backend\n")
    assert p["stack"] == ["python", "fastapi"] and p["roles"] == ["backend"]

def test_unparseable_line_is_rejected_not_ignored():
    with pytest.raises(prof.ProfileError):
        prof.parse_yaml_subset("stack:\n  - python\nthis is not yaml\n")

def test_load_requires_stack_or_roles(tmp_path):
    f = tmp_path / "p.yaml"; f.write_text("remote: true\n")
    with pytest.raises(prof.ProfileError):
        prof.load(f)

def test_load_yaml_and_json_agree(tmp_path):
    y = tmp_path / "p.yaml"; y.write_text("stack:\n  - python\nroles: [backend]\nremote: true\n")
    j = tmp_path / "p.json"; j.write_text('{"stack": ["python"], "roles": ["backend"], "remote": true}')
    a, b = prof.load(y), prof.load(j)
    assert (a.stack, a.roles, a.remote) == (b.stack, b.roles, b.remote)

def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(prof.ProfileError):
        prof.load(tmp_path / "nope.yaml")
