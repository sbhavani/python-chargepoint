# ChargePoint CLI — Tesla Focus PRD

## 1. Overview

**Project Name:** python-chargepoint (CLI enhancements)
**Type:** CLI tool for ChargePoint EV charging network management
**Core Feature:** CLI-first interface with enhanced Tesla support and streamlined workflow
**Target Users:** Tesla owners and EV enthusiasts who use ChargePoint network; power users who prefer CLI over mobile apps

## 2. Motivation

The existing python-chargepoint library provides a full Python API but lacks a convenient config file workflow and a faster CLI stop shortcut. Many Tesla drivers use ChargePoint stations and need quick, scriptable access to:

- Stop charging sessions instantly (e.g., when done early)
- Schedule charging to take advantage of time-of-use rates
- Manage home charger schedules from the terminal
- Store credentials persistently without shell environment variables

## 3. Feature List

### 3.1 Credentials Config File

Store credentials in `~/.config/chargepoint/credentials.toml` instead of relying on environment variables:

```toml
[default]
username = "user@example.com"
coulomb_token = "<coulomb_sess cookie>"

[work]
username = "work@example.com"
coulomb_token = "<work token>"
```

CLI commands accept a `--profile` flag to switch between credential sets.

### 3.2 Quick Stop Shortcut

A top-level `chargepoint stop` command that stops the **currently active** charging session without needing to look up the session ID first:

```bash
chargepoint stop
# → Detects active session and stops it
```

Implementation: calls `get_user_charging_status()`, extracts the active `session_id`, and calls `stop()` in one shot.

### 3.3 Scheduled Charging Commands

New CLI commands for managing scheduled charging:

```bash
# Show current schedule
chargepoint schedule show <charger_id>

# Set a charging schedule (TOU rate optimization)
chargepoint schedule set <charger_id> \
    --weekday-start 23:00 --weekday-end 07:00 \
    --weekend-start 19:00 --weekend-end 15:00

# Disable schedule
chargepoint schedule disable <charger_id>
```

### 3.4 Tesla-Specific Enhancements

Focus on connectors and workflows relevant to Tesla vehicles:

- **Tesla Supercharger status**: Include Tesla-specific connector type (`connector_tesla`, `connector_l2_tesla`) in station filtering
- **Tesla charging session tracking**: Display Tesla-specific metrics (miles/kWh efficiency, charge rate curves)
- **Tesla-compatible connector filter**: `--connector-tesla-l2` and `--connector-tesla-dc` shortcuts for finding Tesla-compatible stations
- **IONNA network support**: Tesla Superchargers on the IONNA network (newly opened to all EVs)

### 3.5 Session Management Shortcuts

```bash
# Start charging on a specific station
chargepoint start <device_id>

# Stop current session (see 3.2)
chargepoint stop

# Show last session summary
chargepoint session last
```

### 3.6 Station Lookup Shortcuts

```bash
# Show nearby Tesla-compatible stations
chargepoint nearby --tesla-l2 --available-only --ne-lat 30.40 --ne-lon -97.64 --sw-lat 30.37 --sw-lon -97.66

# Show station details with Tesla-specific info
chargepoint station <device_id> --format=tesla
```

## 4. CLI Design

### 4.1 Command Structure

```
chargepoint [global options] <command> [args]

Global Options:
  --debug              Enable debug logging
  --json               JSON output
  --profile <name>     Use named credential profile (default: "default")
  --config <path>      Path to config file (default: ~/.config/chargepoint/credentials.toml)
```

### 4.2 Command Inventory

| Command | Description |
|---|---|
| `chargepoint stop` | Stop the currently active charging session |
| `chargepoint start <device_id>` | Start charging on a station |
| `chargepoint session last` | Show the most recent session |
| `chargepoint schedule show <charger_id>` | Show charger schedule |
| `chargepoint schedule set <charger_id> [options]` | Set charger schedule |
| `chargepoint schedule disable <charger_id>` | Disable charger schedule |
| `chargepoint nearby [bounds]` | Find nearby stations |
| `chargepoint station <device_id>` | Show station details |
| `chargepoint account` | Show account info |
| `chargepoint vehicles` | List registered vehicles |

### 4.3 Filter Options (for `nearby`)

| Flag | Description |
|---|---|
| `--connector-tesla` | Tesla proprietary |
| `--connector-tesla-l2` | Tesla Level 2 (NACS) |
| `--connector-tesla-dc` | Tesla Supercharger (DC) |
| `--connector-l2` | Level 2 AC |
| `--connector-combo` | CCS combo (DC) |
| `--dc-fast` | Any DC fast charger |
| `--available-only` | Only available stations |
| `--free-only` | Only free stations |

## 5. Config File Format

```toml
# ~/.config/chargepoint/credentials.toml

[default]
username = "user@example.com"
coulomb_token = "<coulomb_sess cookie>"

[work]
username = "work@company.com"
coulomb_token = "<work coulomb_sess cookie>"
```

The CLI reads from the default profile unless `--profile` is specified.

## 6. Dependencies

No new runtime dependencies. Uses existing library functionality:

- `aiohttp` for async HTTP
- `pydantic` for data models
- `click` for CLI framework

## 7. File Structure

```
python-chargepoint/
├── python_chargepoint/
│   ├── __init__.py
│   ├── __main__.py       # CLI entry point (augmented)
│   └── types.py          # Data models (augmented for Tesla fields)
├── docs/
│   └── PRD.md            # This document
├── README.md             # Updated to reflect CLI enhancements
└── tests/                # Tests for new CLI commands
```

## 8. Success Criteria

- [ ] `chargepoint stop` works without requiring session ID lookup
- [ ] `~/.config/chargepoint/credentials.toml` is loaded automatically
- [ ] `--profile` flag switches between credential sets
- [ ] `chargepoint schedule set/show/disable` work for home chargers
- [ ] `--connector-tesla-l2` and `--connector-tesla-dc` filters work in `nearby`
- [ ] All existing tests pass
- [ ] New commands have test coverage
