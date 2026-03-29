# NightCharge

**Stop your ChargePoint charging session on a schedule.**

ChargePoint's app won't let you set a stop time. NightCharge is the CLI that closes that gap — stop your session at 11 PM, cap it at 80%, or pair it with your utility's off-peak hours. The thing ChargePoint forgot to build.

[![CI](https://github.com/sbhavani/nightcharge/actions/workflows/ci.yml/badge.svg)](https://github.com/sbhavani/nightcharge/actions/workflows/ci.yml)
[![Security](https://github.com/sbhavani/nightcharge/actions/workflows/security.yml/badge.svg)](https://github.com/sbhavani/nightcharge/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://github.com/sbhavani/nightcharge)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](https://github.com/sbhavani/nightcharge/actions/workflows/ci.yml)

## Install

```bash
pip install nightcharge
```

Or from source:

```bash
git clone https://github.com/sbhavani/nightcharge.git
cd nightcharge
uv sync --all-extras
uv run nightcharge --help
```

## The problem

ChargePoint has no scheduled stop. You plug in, and if you don't open the app to hit stop manually, you're charging until dawn — paying peak rates, or hitting a charge limit you didn't want.

## The fix

```bash
# Stop right now — no app needed
nightcharge stop

# Stop at 11 PM (cron)
0 23 * * * nightcharge --profile default stop

# Charge off-peak only (9 PM – 7 AM)
0 21 * * * nightcharge --profile default stop
```

You can also pair it with your car's native scheduled charging to control the *start* time, while NightCharge controls the *stop*.

## Quick start

1. Get a `coulomb_sess` session cookie from ChargePoint:
   - Log into [driver.chargepoint.com](https://driver.chargepoint.com)
   - DevTools → Application → Cookies → `driver.chargepoint.com` → copy `coulomb_sess`

2. Add to `~/.config/nightcharge/credentials.toml`:

```toml
[default]
username = "you@example.com"
coulomb_token = "your_coulomb_sess_value"
```

3. Use it:

```bash
nightcharge account       # Check your account
nightcharge stop         # Stop the active session
nightcharge session last  # See your last charge
nightcharge charger list  # Find your home charger ID
nightcharge charger status <id>   # Check charger state
nightcharge charger set-schedule <id> \
    --weekday-start 23:00 --weekday-end 07:00 \
    --weekend-start 21:00 --weekend-end 09:00
```

## Credentials

Credentials are loaded in this priority order:

1. **Config file** (`~/.config/nightcharge/credentials.toml`) — recommended
2. **Environment variables** — `CP_USERNAME`, `CP_COULOMB_TOKEN`
3. **Password prompt** — interactive (requires captcha bypass)

Use multiple profiles for multiple accounts:

```toml
[default]
username = "personal@example.com"
coulomb_token = "..."

[work]
username = "work@corp.com"
coulomb_token = "..."
```

```bash
nightcharge --profile work stop
```

## CLI reference

```
nightcharge [--debug] [--json] [--profile <name>] <command>
```

**Global options**

| Option | Description |
|---|---|
| `--debug` | Verbose logging |
| `--json` | Raw JSON output |
| `--profile` | Credential profile (default: "default") |
| `--config` | Config file path (default: `~/.config/nightcharge/credentials.toml`) |

**Quick actions**

```bash
nightcharge stop                              # Stop the active session
nightcharge session last                       # Most recent session summary
nightcharge session start <device_id>          # Start charging on a station
nightcharge session stop <session_id>          # Stop by session ID
nightcharge session get <session_id>          # Session details
```

**Account & vehicle**

```bash
nightcharge account
nightcharge vehicles
nightcharge charging-status
```

**Home charger**

```bash
nightcharge charger list                       # List charger IDs
nightcharge charger status <id>                # Charging state, amperage
nightcharge charger tech-info <id>             # Firmware, serial, MAC
nightcharge charger config <id>                # LED settings, utility info
nightcharge charger set-amperage <id> <amps> # Set charge limit (e.g. 24 A)
nightcharge charger set-led <id> <level>     # LED: 0=off 5=100%
nightcharge charger restart <id>              # Reboot charger
nightcharge charger schedule <id>              # Show current schedule
nightcharge charger set-schedule <id> \
    --weekday-start 23:00 --weekday-end 07:00 \
    --weekend-start 21:00 --weekend-end 09:00
nightcharge charger disable-schedule <id>
```

**Stations**

```bash
nightcharge station <device_id>                # Station details
nightcharge nearby --sw-lat 30.37 --sw-lon -97.66 \
                   --ne-lat 30.40 --ne-lon -97.64 \
    [--connector-l2] [--connector-combo] \
    [--connector-chademo] [--connector-tesla] \
    [--dc-fast] [--available-only] [--free-only]
```

### Tesla support

Find Superchargers open to all EVs (IONNA network):

```bash
nightcharge nearby --dc-fast --available-only \
    --sw-lat 30.37 --sw-lon -97.66 --ne-lat 30.40 --ne-lon -97.64
```

Filter for NACS (Tesla connector used by most non-Tesla EVs):

```bash
nightcharge nearby --connector-tesla --available-only ...
```

## Development

```bash
git clone https://github.com/sbhavani/nightcharge.git
cd nightcharge
uv sync --all-extras
uv run pre-commit install
uv run pytest
```

Requires Python 3.12.

### Checks

```bash
uv run black --check nightcharge/ tests/
uv run flake8 nightcharge/ tests/
uv run mypy nightcharge/
uv run pyright nightcharge/
uv run tox -e pip-audit
```

## Disclaimer

This project is not affiliated with or endorsed by ChargePoint, Inc. Use at your own risk. ChargePoint is a registered trademark.
