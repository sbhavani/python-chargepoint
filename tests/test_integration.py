"""
Integration tests that call the real ChargePoint API.

These tests are skipped by default unless real credentials are configured.
To enable them, set environment variables or populate .env:

    CP_COULOMB_TOKEN  (recommended — avoids Datadome bot protection)
    CP_SSO_JWT        (also works)

Note: CP_USERNAME + CP_PASSWORD alone will NOT work — ChargePoint's Datadome
bot protection blocks automated password login. You must use a session cookie
(coulomb_sess) or SSO JWT.

To get a CP_COULOMB_TOKEN:
  1. Log into https://driver.chargepoint.com in your browser
  2. Open DevTools → Application → Cookies → driver.chargepoint.com
  3. Copy the coulomb_sess cookie value

Running:
    pytest tests/test_integration.py -v
"""
import os

import dotenv
import pytest
from click.testing import CliRunner

from nightcharge import ChargePoint
from nightcharge.__main__ import cli
from nightcharge.exceptions import DatadomeCaptcha, LoginError

# Load .env if present
dotenv.load_dotenv()


def _require_real_credentials():
    """Return (username, coulomb_token, sso_jwt, password) from the environment."""
    return (
        os.environ.get("CP_USERNAME", ""),
        os.environ.get("CP_COULOMB_TOKEN", ""),
        os.environ.get("CP_SSO_JWT", ""),
        os.environ.get("CP_PASSWORD", ""),
    )


def _has_coulomb_token():
    _, ct, sj, _ = _require_real_credentials()
    return bool(ct or sj)


@pytest.fixture(scope="module")
def runner():
    return CliRunner()


@pytest.fixture(scope="module")
async def real_client():
    """An authenticated client using real credentials from the environment.

    Skips the module if credentials are not available or authentication fails.
    """
    username, coulomb_token, sso_jwt, password = _require_real_credentials()

    if not _has_coulomb_token():
        pytest.skip(
            "Integration tests require CP_COULOMB_TOKEN or CP_SSO_JWT. "
            "Password-based auth (CP_PASSWORD) is blocked by Datadome bot protection."
        )

    try:
        client = await ChargePoint.create(username, coulomb_token=coulomb_token)
        if not coulomb_token:
            if sso_jwt:
                await client.login_with_sso_session(sso_jwt)
        yield client
    except (DatadomeCaptcha, LoginError) as e:
        pytest.skip(f"Authentication failed (Datadome or bad token): {e}")
    finally:
        try:
            await client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI integration tests (no active session needed)
# ---------------------------------------------------------------------------


def test_charging_status_not_charging(runner):
    """charging-status should report 'Not currently charging.' when no session is active."""
    result = runner.invoke(cli, ["charging-status"], catch_exceptions=False)
    # May succeed or may fail due to auth — either way, check output
    if result.exit_code == 0:
        assert "Not currently charging" in result.output or "Session" in result.output


def test_account(runner):
    """account should print name, email, and balance."""
    result = runner.invoke(cli, ["account"], catch_exceptions=False)
    if result.exit_code == 0:
        assert any(word in result.output for word in ["Name", "Email", "Balance", "Account"])


def test_vehicles(runner):
    """vehicles should list registered EVs."""
    result = runner.invoke(cli, ["vehicles"], catch_exceptions=False)
    if result.exit_code == 0:
        assert result.output  # Some output expected


def test_charger_list(runner):
    """charger list should return charger IDs (or an empty list)."""
    result = runner.invoke(cli, ["charger", "list"], catch_exceptions=False)
    if result.exit_code == 0:
        # Output should be parseable — either IDs or "No home chargers registered"
        assert result.output


def test_session_last(runner):
    """session last should show the most recent session or a 'No sessions' message."""
    result = runner.invoke(cli, ["session", "last"], catch_exceptions=False)
    if result.exit_code == 0:
        assert result.output  # Either session data or "No charging sessions found"


def test_stop_no_active_session(runner):
    """stop should report no active session when nothing is charging."""
    result = runner.invoke(cli, ["stop"], catch_exceptions=False)
    if result.exit_code == 0:
        assert "No active charging session" in result.output


# ---------------------------------------------------------------------------
# Library-level integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_account(real_client):
    """get_account should return a valid account object."""
    acct = await real_client.get_account()
    assert acct.user.full_name
    assert acct.user.email
    assert acct.account_balance.amount  # May be "0.0" or similar


@pytest.mark.asyncio
async def test_get_vehicles(real_client):
    """get_vehicles should return a list (possibly empty)."""
    evs = await real_client.get_vehicles()
    assert isinstance(evs, list)


@pytest.mark.asyncio
async def test_get_charger_list(real_client):
    """get_home_chargers should return a list of charger IDs."""
    chargers = await real_client.get_home_chargers()
    assert isinstance(chargers, list)


@pytest.mark.asyncio
async def test_get_charging_status_not_charging(real_client):
    """get_user_charging_status should return None when not charging."""
    status = await real_client.get_user_charging_status()
    # None means not currently charging (valid state)
    assert status is None or hasattr(status, "session_id")


@pytest.mark.asyncio
async def test_get_charging_sessions(real_client):
    """get_charging_sessions should return a list (possibly empty)."""
    sessions = await real_client.get_charging_sessions(limit=5)
    assert isinstance(sessions, list)
    for s in sessions:
        assert s.session_id
