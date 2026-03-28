# python-chargepoint — Roadmap

## Background

ChargePoint's app and web UI don't let you stop a charging session on a schedule — the core reason this project exists. This document captures the current implementation status and prioritized roadmap.

---

## Implementation Status

### Done

| Feature | Location | Notes |
|---|---|---|
| `chargepoint stop` | `__main__.py:stop` | Stops active session without needing session ID |
| `chargepoint session start <device_id>` | `__main__.py:session_start` | Start on any station |
| `chargepoint session stop <session_id>` | `__main__.py:session_stop` | Stop by session ID |
| `chargepoint session get <session_id>` | `__main__.py:session_get` | Session details |
| `chargepoint charger schedule` | `__main__.py:charger_schedule` | Show charger schedule |
| `chargepoint charger set-schedule` | `__main__.py:charger_set_schedule` | Set TOU schedule |
| `chargepoint charger disable-schedule` | `__main__.py:charger_disable_schedule` | Disable schedule |
| All home charger commands | `charger` subgroup | list, status, tech-info, config, set-amperage, set-led, restart |
| Credentials config file | `__main__.py:_load_config` | TOML at `~/.config/chargepoint/credentials.toml` |
| `--profile` / `--config` global flags | `cli()` | |
| All station/account/vehicle commands | `__main__.py` | Pre-existing |

### Not Done

| Feature | Status |
|---|---|
| Top-level `schedule` subcommand | Currently `charger schedule / set-schedule / disable-schedule` |
| `chargepoint session last` | Not implemented |
| `chargepoint start <device_id>` shortcut | Currently `session start` |
| `--connector-tesla-l2` filter | API supports `connector_l2_tesla` in MapFilter but CLI flag missing |
| `--connector-tesla-dc` filter | API supports IONNA but CLI flag missing |
| `chargepoint station <id> --format=tesla` | Not implemented |

---

## Roadmap (MoSCoW)

### Must Have

**`chargepoint stop`** — the project's reason for existing.
Status: ✅ Done.

**Credentials config file** (`~/.config/chargepoint/credentials.toml`)
Most users won't want to manage shell environment variables for a CLI they run from cron. A TOML config file with profile support removes friction.

```toml
[default]
username = "user@example.com"
coulomb_token = "<token>"

[work]
username = "work@corp.com"
coulomb_token = "<token>"
```

- `--profile <name>` global flag to switch between profiles
- `--config <path>` to specify a non-default config file
- Falls back to env vars if config file doesn't exist
- No new dependencies (use stdlib `tomllib` on Python 3.11+)

**`chargepoint session last`**
Often you don't know the session ID. A shortcut to show the most recent session (or all sessions sorted by start time) lets users inspect what they just did without digging through the app.

```bash
chargepoint session last
# → Session: 12345678
#   Device:  Home Flex (device 99999999)
#   State:   stopped
#   Energy:  42.123 kWh
#   Miles:   +142.3 mi
#   Cost:    $12.34 USD
```

### Should Have

**Top-level `schedule` subcommand**

Currently: `chargepoint charger schedule <id>`
Proposed: `chargepoint schedule show/set/disable <charger_id>`

A top-level `schedule` group matches how `charger` and `session` are organized and makes the command easier to discover. The charger subcommands remain as aliases for backwards compatibility.

**`chargepoint start <device_id>` shortcut**

Currently: `chargepoint session start <device_id>`
Proposed: `chargepoint start <device_id>` as a shortcut

Both forms work; the shortcut is faster for power users.

**Tesla connector filters**

The `MapFilter` type already has `connector_l2_tesla` and the API supports `network_ionna` for Tesla Superchargers open to all EVs. The CLI just needs the flag additions:

| Flag | Maps to | Description |
|---|---|---|
| `--connector-tesla-l2` | `connector_l2_tesla=True` | Tesla Level 2 (NACS) |
| `--connector-tesla-dc` | `network_ionna=True` + `dc_fast=True` | Tesla Supercharger (IONNA) |

### Could Have

**`chargepoint station <id> --format=tesla`**
Display station info tailored to Tesla vehicles — show NACS compatibility, Supercharger status, IONNA network label.

**Scheduled stop via a daemon or systemd timer template**
Document how to pair `chargepoint stop` with system timers for:
- Stop at a fixed time (cron: `0 23 * * * chargepoint stop`)
- Stop when SOC reaches a target (requires polling, document a reference script)

### Won't Have (for now)

- **Web dashboard / UI** — out of scope; this is a CLI/API project
- **SOC-based stop** — would require polling and is vehicle-specific; a reference script in the docs is the right approach

---

## Dependencies

No new runtime dependencies. Uses existing stack:
- `aiohttp` — async HTTP
- `pydantic` — data models
- `click` — CLI framework
- `tomllib` — stdlib config parsing (Python 3.11+; `tomli` backport for 3.10)
