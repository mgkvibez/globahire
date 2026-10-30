# Contributing

## Running things

```bash
python -m pip install -e ".[dev]"
bash scripts/verify.sh      # install, version, tests, offline smoke
```

## Adding a board

1. Write a parser: `(payload) -> List[Job]` in `globahire/sources.py`.
2. Save a real (trimmed) payload under `tests/fixtures/`.
3. Register it in `SOURCES` and extend `detect_source`.
4. Add a test that parses the fixture and asserts the normalised fields.

Rules: never call the network from a parser or a test; only public token-free
endpoints or documented board tokens; if a board requires a logged-in session,
it is out of scope.

## Not in scope

Auto-applying, headless browsers, and scraping logged-in boards. See the README
for why.
