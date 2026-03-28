import logging
from datetime import datetime
from typing import Optional

import pytest

from python_chargepoint import ChargePoint
from python_chargepoint.global_config import GlobalConfiguration
from python_chargepoint.session import ChargingSession, _send_command
from python_chargepoint.exceptions import CommunicationError, APIError


def _add_start_function_responses(
    aioresponses,
    global_config: GlobalConfiguration,
    session_id: Optional[int] = 12345,
) -> None:
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/startsession",
        status=200,
        payload={"ackId": 1},
    )
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/session/ack",
        status=200,
        payload={"sessionId": session_id},
    )


async def test_get_session(charging_session: ChargingSession, timestamp: datetime):
    assert charging_session.session_id == 1
    assert charging_session.utility.name == "Power Company"
    assert len(charging_session.update_data) == 1
    assert charging_session.update_data[0].timestamp == timestamp


async def test_send_command_invalid_action():
    with pytest.raises(AttributeError):
        await _send_command(action="invalid", client=None, device_id=1)


async def test_stop_session_failure(
    aioresponses,
    global_config: GlobalConfiguration,
    charging_session: ChargingSession,
):
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/stopSession",
        status=400,
    )

    with pytest.raises(CommunicationError) as exc:
        await charging_session.stop()

    assert exc.value.response.status == 400


async def test_stop_session(
    aioresponses,
    global_config: GlobalConfiguration,
    charging_session: ChargingSession,
    caplog,
):
    caplog.set_level(logging.INFO)
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/stopSession",
        status=200,
        payload={"ackId": 1},
    )
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/session/ack",
        status=200,
        payload={},
    )

    assert await charging_session.stop() is None
    assert "Successfully confirmed stop command." in caplog.text


async def test_stop_session_ack_failure(
    aioresponses,
    global_config: GlobalConfiguration,
    charging_session: ChargingSession,
):
    """stop() should raise CommunicationError when the ack endpoint returns a non-200 status."""
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/stopSession",
        status=200,
        payload={"ackId": 1},
    )
    # The ack endpoint returns 403 on every poll attempt (all 20 retries fail)
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/session/ack",
        status=403,
        payload={"error": "failed to stop session"},
    )

    with pytest.raises(CommunicationError) as exc:
        await charging_session.stop()

    # _raise_for_status formats the message as "FORBIDDEN: [POST] <url>"
    assert "FORBIDDEN" in str(exc.value)
    assert exc.value.response.status == 403


async def test_stop_session_ack_non_json(
    aioresponses,
    global_config: GlobalConfiguration,
    charging_session: ChargingSession,
):
    """stop() should handle non-JSON ack responses gracefully (except Exception: pass)."""
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/stopSession",
        status=200,
        payload={"ackId": 1},
    )
    # Return a plain-text 403 — json() will raise, triggering except Exception: pass
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/session/ack",
        status=403,
        body="Internal Server Error",
    )

    with pytest.raises(CommunicationError) as exc:
        await charging_session.stop()

    assert exc.value.response.status == 403


async def test_start_session(
    aioresponses,
    authenticated_client: ChargePoint,
    user_charging_status_json: dict,
    charging_status_json: dict,
    caplog,
):
    caplog.set_level(logging.INFO)
    _add_start_function_responses(
        aioresponses=aioresponses,
        global_config=authenticated_client.global_config,
    )

    aioresponses.post(
        f"{authenticated_client.global_config.endpoints.mapcache_endpoint}v2",
        status=200,
        payload={"user_status": user_charging_status_json},
    )
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions/1",
        status=200,
        payload={"charging_status": charging_status_json},
    )

    new = await ChargingSession.start(client=authenticated_client, device_id=1)
    assert new.session_id == 1
    assert "Successfully confirmed start command." in caplog.text


async def test_get_charging_session_error(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions/1",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_charging_session(session_id=1)

    assert exc.value.response.status == 500


async def test_get_charging_session_error_body(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions/1",
        status=200,
        payload={"charging_status": {"error": "java.lang.NullPointerException"}},
    )

    with pytest.raises(CommunicationError):
        await authenticated_client.get_charging_session(session_id=1)


async def test_get_charging_session_no_utility(
    aioresponses, authenticated_client: ChargePoint, charging_status_json: dict
):
    charging_status_json["utility"] = None

    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions/1",
        status=200,
        payload={"charging_status": charging_status_json},
    )

    session = await authenticated_client.get_charging_session(session_id=1)
    assert session.utility is None


async def test_get_charging_session_no_pricing_spec_id(
    aioresponses, authenticated_client: ChargePoint, charging_status_partial_json: dict
):
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions/1",
        status=200,
        payload={"charging_status": charging_status_partial_json},
    )

    session = await authenticated_client.get_charging_session(session_id=1)
    assert session.pricing_spec_id == 0


async def test_start_session_no_active_charging(
    aioresponses,
    authenticated_client: ChargePoint,
    global_config: GlobalConfiguration,
):
    """ChargingSession.start should raise APIError when no session is active."""
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/startsession",
        status=200,
        payload={"ackId": 1},
    )
    aioresponses.post(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/station/session/ack",
        status=200,
        payload={"sessionId": 12345},
    )
    # get_user_charging_status returns None when the API response has no user_status
    aioresponses.post(
        authenticated_client.global_config.endpoints.mapcache_endpoint / "v2",
        status=200,
        payload={"user_status": None},
    )

    with pytest.raises(APIError) as exc:
        await ChargingSession.start(device_id=1, client=authenticated_client)

    assert "No active charging session found" in str(exc.value)
