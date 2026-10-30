# Changelog

## v0.1.0 - 2026-10-30

- Radar only: fetch public boards, filter against `profile.yaml`, announce new
  matches, remember them. No applications are ever sent.
- Boards: remotive, arbeitnow, greenhouse (needs `--board`), lever (needs
  `--board`). Parsers are pure functions, so the suite never touches a network.
- Notifiers: terminal, generic webhook (Slack/Discord shape), Telegram. Injected
  transports in tests.
- Profile reader is a small, strict YAML subset; it rejects what it cannot parse
  instead of dropping a filter.
- Dedupe by stable company+title+location hash, atomic state file, one alert per
  real role.
- Exit codes: 0 nothing new, 3 new matches, 2 configuration error.
