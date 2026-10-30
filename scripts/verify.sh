#!/usr/bin/env bash
# Release gate for globahire: run before every push that claims "done".
# Four independent checks. The smoke replays a saved board payload so the gate
# never touches the network, and asserts the documented exit code (3 = matches).
set -uo pipefail
cd "$(dirname "$0")/.."

fail() { echo "GATE FAILED: $*"; exit 1; }

echo "== check 1/4: editable install"
python3 -m pip install -q -e ".[dev]" || fail "install"

echo "== check 2/4: version consistency (pyproject vs module)"
pv=$(python3 - <<'PY'
import pathlib, re
try:
    import tomllib
    print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])
except ModuleNotFoundError:
    text = pathlib.Path("pyproject.toml").read_text()
    print(re.search(r'(?m)^version\s*=\s*"([^"]+)"', text).group(1))
PY
)
mv=$(python3 -c "import globahire;print(globahire.__version__)")
[ "$pv" = "$mv" ] || { echo "pyproject says $pv, module says $mv"; fail "version drift"; }
echo "version $pv consistent"

echo "== check 3/4: test suite"
python3 -m pytest -q || fail "tests"

echo "== check 4/4: offline radar smoke (expects exit 3)"
work=$(mktemp -d)
out="$work/out.txt"
python3 -m globahire.cli check --profile examples/profile.example.yaml \
    --from-fixture tests/fixtures/remotive.json --state "$work/seen.json" > "$out" 2>&1
code=$?
if [ "$code" != "3" ]; then echo "expected exit 3, got $code"; cat "$out"; rm -r "$work"; fail "check exit code"; fi
grep -q "Backend Engineer" "$out" || { cat "$out"; rm -r "$work"; fail "match missing"; }
# second pass must announce nothing: dedupe is part of the product
python3 -m globahire.cli check --profile examples/profile.example.yaml \
    --from-fixture tests/fixtures/remotive.json --state "$work/seen.json" > "$work/out2.txt" 2>&1
code2=$?
[ "$code2" = "0" ] || { echo "second pass expected exit 0, got $code2"; cat "$work/out2.txt"; rm -r "$work"; fail "dedupe"; }
rm -r "$work"
echo "smoke ok (exit 3 then 0: matched once, silent after)"
echo "ALL CHECKS PASSED"
