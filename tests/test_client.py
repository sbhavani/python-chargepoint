import logging

import pytest

from python_chargepoint import ChargePoint
from python_chargepoint.global_config import GlobalConfiguration
from python_chargepoint.constants import DISCOVERY_API
from python_chargepoint.exceptions import (
    LoginError,
    CommunicationError,
    DatadomeCaptcha,
    InvalidSession,
)

from .test_session import _add_start_function_responses


async def test_client_auth_wrapper(aioresponses, authenticated_client: ChargePoint):
    aioresponses.post(
        f"{authenticated_client.global_config.endpoints.sso_endpoint}v1/user/logout",
        payload={},
    )

    await authenticated_client.logout()
    with pytest.raises(RuntimeError):
        await authenticated_client.get_home_chargers()


async def test_client_login_with_password_failure(
    aioresponses, global_config_json: dict, global_config: GlobalConfiguration
):
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.post(
        f"{global_config.endpoints.sso_endpoint}v1/user/login",
        status=500,
    )

    with pytest.raises(LoginError) as exc:
        client = await ChargePoint.create("test")
        await client.login_with_password("demo")

    assert exc.value.response.status == 500


async def test_client_login_with_password(
    aioresponses,
    global_config_json: dict,
    global_config: GlobalConfiguration,
    account_json: dict,
):
    coulomb_token = "rAnDomBaSe64EnCodEdDaTaToKeNrAnDomBaSe64EnCodEdD#D???????#RNA-US"
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.post(
        f"{global_config.endpoints.sso_endpoint}v1/user/login",
        status=200,
        headers={
            "Set-Cookie": f"coulomb_sess={coulomb_token}; Domain=.chargepoint.com; Path=/"
        },
    )
    aioresponses.get(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=200,
        payload=account_json,
    )

    client = await ChargePoint.create("test")
    await client.login_with_password("demo")

    assert client.coulomb_token == coulomb_token
    assert client.user_id == account_json["user"]["userId"]


async def test_client_unable_to_discover(aioresponses):
    aioresponses.post(DISCOVERY_API, status=500)
    with pytest.raises(CommunicationError) as exc:
        await ChargePoint.create("foo", "bar")

    assert exc.value.response.status == 500


async def test_client_expired_session(
    aioresponses,
    global_config_json: dict,
    global_config: GlobalConfiguration,
    account_json: dict,
):
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.get(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=200,
        payload=account_json,
    )
    aioresponses.get(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=401,
    )

    client = await ChargePoint.create(
        username="test",
        coulomb_token="rAnDomBaSe64EnCodEdDaTaToKeNrAnDomBaSe64EnCodEdD#D???????#RNA-US",
    )
    with pytest.raises(InvalidSession) as exc:
        await client.get_account()

    assert exc.value.response.status == 401


async def test_client_with_coulomb_token(
    aioresponses,
    global_config_json: dict,
    global_config: GlobalConfiguration,
    account_json: dict,
):
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.get(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=200,
        payload=account_json,
    )

    coulomb_token = "rAnDomBaSe64EnCodEdDaTaToKeNrAnDomBaSe64EnCodEdD#D???????#RNA-US"

    client = await ChargePoint.create(username="test", coulomb_token=coulomb_token)

    assert client.coulomb_token == coulomb_token
    assert client.user_id == account_json["user"]["userId"]


async def test_request_refreshes_coulomb_token(
    aioresponses,
    authenticated_client: ChargePoint,
    account_json: dict,
    global_config: GlobalConfiguration,
):
    """Server returns coulomb_sess with Max-Age=7200 on every response.
    _request must re-set it without expiry so the cookie is never evicted."""
    new_token = "rEfReSheDbAsE64EnCodEdDaTaToKeNrEfReSheDbAsE64En#D???????#RNA-US"
    aioresponses.get(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=200,
        payload=account_json,
        headers={"Set-Cookie": f"coulomb_sess={new_token}; Max-Age=7200; Path=/"},
    )

    await authenticated_client.get_account()

    assert authenticated_client.coulomb_token == new_token


async def test_client_login_with_password_datadome(
    aioresponses, global_config_json: dict, global_config: GlobalConfiguration
):
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.post(
        f"{global_config.endpoints.sso_endpoint}v1/user/login",
        status=403,
        payload={"url": "https://geo.captcha-delivery.com/captcha/?initialCid=123"},
        content_type="application/json",
    )

    with pytest.raises(DatadomeCaptcha) as exc:
        client = await ChargePoint.create("test")
        await client.login_with_password("demo")

    assert "captcha-delivery.com" in exc.value.captcha


async def test_client_login_with_sso(
    aioresponses,
    global_config_json: dict,
    global_config: GlobalConfiguration,
    account_json: dict,
):
    coulomb_token = "rAnDomBaSe64EnCodEdDaTaToKeNrAnDomBaSe64EnCodEdD#D???????#RNA-US"
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.get(
        f"{global_config.endpoints.portal_domain_endpoint}index.php/nghelper/getSession",
        status=200,
        headers={
            "Set-Cookie": f"coulomb_sess={coulomb_token}; Domain=.chargepoint.com; Path=/"
        },
    )
    aioresponses.get(
        f"{global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=200,
        payload=account_json,
    )

    client = await ChargePoint.create("test")
    await client.login_with_sso_session("some-sso-jwt")

    assert client.coulomb_token == coulomb_token
    assert client.user_id == account_json["user"]["userId"]


async def test_client_login_with_sso_failure(
    aioresponses,
    global_config_json: dict,
    global_config: GlobalConfiguration,
):
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.get(
        f"{global_config.endpoints.portal_domain_endpoint}index.php/nghelper/getSession",
        status=401,
    )

    with pytest.raises(InvalidSession):
        client = await ChargePoint.create("test")
        await client.login_with_sso_session("bad-jwt")


async def test_client_logout_failed(aioresponses, authenticated_client: ChargePoint):
    aioresponses.post(
        f"{authenticated_client.global_config.endpoints.sso_endpoint}v1/user/logout",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.logout()

    assert exc.value.response.status == 500


async def test_client_get_account(
    aioresponses, authenticated_client: ChargePoint, account_json: dict
):
    aioresponses.get(
        f"{authenticated_client.global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=200,
        payload=account_json,
    )

    acct = await authenticated_client.get_account()
    assert acct.user.user_id == 1234567890


async def test_client_get_account_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        f"{authenticated_client.global_config.endpoints.accounts_endpoint}v1/driver/profile/user",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_account()

    assert exc.value.response.status == 500


async def test_client_get_vehicles(
    aioresponses, authenticated_client: ChargePoint, electric_vehicle_json: dict
):
    aioresponses.get(
        f"{authenticated_client.global_config.endpoints.accounts_endpoint}v1/driver/vehicle",
        status=200,
        payload=[electric_vehicle_json],
    )

    evs = await authenticated_client.get_vehicles()
    assert len(evs) == 1
    assert evs[0].color == "Green"


async def test_client_get_vehicles_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        f"{authenticated_client.global_config.endpoints.accounts_endpoint}v1/driver/vehicle",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_vehicles()

    assert exc.value.response.status == 500


async def test_client_get_home_chargers(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers",
        status=200,
        payload={
            "data": [
                {
                    "id": "1234567890",
                    "label": None,
                    "protocolIdentifier": None,
                    "coordinates": None,
                    "location": None,
                }
            ],
            "pagination": {"nextCursor": "none"},
        },
    )

    chargers = await authenticated_client.get_home_chargers()

    assert len(chargers) == 1
    assert chargers[0] == 1234567890


async def test_client_get_home_chargers_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_home_chargers()

    assert exc.value.response.status == 500


async def test_client_get_home_charger_status(
    aioresponses, authenticated_client: ChargePoint, home_charger_json: dict
):
    aioresponses.get(
        f"{authenticated_client.global_config.endpoints.hcpo_hcm_endpoint}api/v1/configuration/users/1/chargers/1234567890/status",
        status=200,
        payload=home_charger_json,
    )

    charger = await authenticated_client.get_home_charger_status(1234567890)

    assert charger.charger_id == 1234567890
    assert charger.amperage_limit == 28
    assert charger.is_plugged_in is True


async def test_client_get_home_charger_status_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        f"{authenticated_client.global_config.endpoints.hcpo_hcm_endpoint}api/v1/configuration/users/1/chargers/1234567890/status",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_home_charger_status(1234567890)

    assert exc.value.response.status == 500


async def test_client_get_home_charger_technical_info(
    aioresponses,
    authenticated_client: ChargePoint,
    home_charger_tech_info_json: dict,
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers/1234567890/technical-info",
        status=200,
        payload=home_charger_tech_info_json,
    )

    tech = await authenticated_client.get_home_charger_technical_info(1234567890)

    assert tech.software_version == "1.2.3.4"
    assert tech.model_number == "CPH50-NEMA6-50-L23"
    assert tech.stop_charge_supported is True


async def test_client_get_home_charger_technical_info_failure(
    aioresponses,
    authenticated_client: ChargePoint,
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers/1234567890/technical-info",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_home_charger_technical_info(1234567890)

    assert exc.value.response.status == 500


async def test_client_get_user_charging_status(
    aioresponses,
    authenticated_client: ChargePoint,
    user_charging_status_json: dict,
):
    aioresponses.post(
        f"{authenticated_client.global_config.endpoints.mapcache_endpoint}v2",
        status=200,
        payload={"user_status": user_charging_status_json},
    )

    status = await authenticated_client.get_user_charging_status()

    assert status is not None
    assert status.session_id == 1


async def test_client_set_amperage_limit(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/chargers/1234567890/charge-amperage-limit",
        status=200,
        payload={
            "name": "Charge Amperage Limit",
            "desiredValue": "28",
            "status": "APPLYING",
        },
    )

    assert await authenticated_client.set_amperage_limit(1234567890, 28) is None

    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/chargers/1234567890/charge-amperage-limit",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.set_amperage_limit(1234567890, 0)

    assert exc.value.response.status == 500


async def test_client_set_led_brightness(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/chargers/1234567890/led-brightness",
        status=200,
        payload={"name": "LED Brightness", "desiredValue": "4", "status": "APPLYING"},
    )

    assert await authenticated_client.set_led_brightness(1234567890, 4) is None

    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/chargers/1234567890/led-brightness",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.set_led_brightness(1234567890, 4)

    assert exc.value.response.status == 500


async def test_client_get_user_charging_status_not_charging(
    aioresponses,
    authenticated_client: ChargePoint,
):
    aioresponses.post(
        f"{authenticated_client.global_config.endpoints.mapcache_endpoint}v2",
        status=200,
        payload={"user_status": {}},
    )

    status = await authenticated_client.get_user_charging_status()

    assert status is None


async def test_client_get_get_user_charging_status_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.post(
        f"{authenticated_client.global_config.endpoints.mapcache_endpoint}v2",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_user_charging_status()

    assert exc.value.response.status == 500


async def test_client_restart_home_charger(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.post(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers/1234567890/restart",
        status=200,
    )

    assert await authenticated_client.restart_home_charger(1234567890) is None


async def test_client_restart_home_charger_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.post(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers/1234567890/restart",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.restart_home_charger(1234567890)

    assert exc.value.response.status == 500


async def test_client_get_home_charger_config(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers/1234567890/configurations",
        status=200,
        payload={
            "settings": {
                "serialNumber": "214841066755",
                "macAddress": "0024B100000698BA",
                "stationNickname": "ChargePoint Home",
                "streetAddress": "123 Main St",
                "hasUtilityInfo": True,
                "utility": {
                    "id": 22,
                    "name": "Austin Energy",
                    "plans": [
                        {
                            "id": 80693,
                            "name": "Residential",
                            "code": "R",
                            "isEvPlan": False,
                        }
                    ],
                },
                "indicatorLightEcoMode": "OFF",
                "flashlightReset": False,
                "worksWithNest": False,
                "isPairedWithNest": False,
                "isInstalledByInstaller": False,
                "led": {
                    "brightness": {
                        "level": "5",
                        "inProgress": False,
                        "supportedLevels": ["0", "1", "2", "3", "4", "5"],
                        "isEnabled": True,
                    }
                },
            }
        },
    )

    config = await authenticated_client.get_home_charger_config(1234567890)

    assert config.serial_number == "214841066755"
    assert config.station_nickname == "ChargePoint Home"
    assert config.utility.name == "Austin Energy"
    assert config.led_brightness.level == 5
    assert config.led_brightness.supported_levels == [0, 1, 2, 3, 4, 5]


async def test_client_get_home_charger_config_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/configuration/users/1/chargers/1234567890/configurations",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_home_charger_config(1234567890)

    assert exc.value.response.status == 500


async def test_client_get_home_charger_schedule(
    aioresponses, authenticated_client: ChargePoint, home_charger_schedule_json: dict
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/schedule/charger/1234567890/schedule",
        status=200,
        payload=home_charger_schedule_json,
    )

    schedule = await authenticated_client.get_home_charger_schedule(1234567890)

    assert schedule.schedule_enabled is False
    assert schedule.has_utility_info is True
    assert schedule.default_schedule is not None
    assert schedule.default_schedule.weekdays.start_time == "23:00"
    assert schedule.default_schedule.weekdays.end_time == "07:00"
    assert schedule.default_schedule.weekends.start_time == "19:00"
    assert schedule.default_schedule.weekends.end_time == "15:00"


async def test_client_get_home_charger_schedule_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/schedule/charger/1234567890/schedule",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_home_charger_schedule(1234567890)

    assert exc.value.response.status == 500


async def test_client_set_home_charger_schedule(
    aioresponses,
    authenticated_client: ChargePoint,
    home_charger_schedule_set_json: dict,
):
    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/schedule/charger/1234567890/schedule",
        status=200,
        payload=home_charger_schedule_set_json,
    )

    schedule = await authenticated_client.set_home_charger_schedule(
        1234567890, "23:00", "07:00", "19:00", "15:00"
    )

    assert schedule.schedule_enabled is True
    assert schedule.user_schedule is not None
    assert schedule.user_schedule.weekdays.start_time == "23:00"
    assert schedule.user_schedule.weekdays.end_time == "07:00"
    assert schedule.user_schedule.weekends.start_time == "19:00"
    assert schedule.user_schedule.weekends.end_time == "15:00"


async def test_client_set_home_charger_schedule_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/schedule/charger/1234567890/schedule",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.set_home_charger_schedule(
            1234567890, "23:00", "07:00", "19:00", "15:00"
        )

    assert exc.value.response.status == 500


async def test_client_disable_home_charger_schedule(
    aioresponses, authenticated_client: ChargePoint, home_charger_schedule_json: dict
):
    aioresponses.put(
        authenticated_client.global_config.endpoints.hcpo_hcm_endpoint
        / "api/v1/schedule/charger/1234567890/schedule",
        status=200,
        payload={**home_charger_schedule_json, "scheduleEnabled": False},
    )

    schedule = await authenticated_client.disable_home_charger_schedule(1234567890)

    assert schedule.schedule_enabled is False


async def test_client_get_station(
    aioresponses, authenticated_client: ChargePoint, station_info_json: dict
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.mapcache_endpoint
        / "v3/station/info"
        % {"deviceId": "99991111", "use_cache": "false"},
        status=200,
        payload=station_info_json,
    )

    info = await authenticated_client.get_station(99991111)

    assert info.device_id == 99991111
    assert info.name == ["TEST STATION", "PORT A"]
    assert info.address.city == "Testville"
    assert info.station_status_v2 == "available"
    assert info.ports_info.port_count == 1
    assert info.ports_info.ports[0].status_v2 == "available"
    assert info.ports_info.ports[0].power_range.max == 7.2
    assert info.ports_info.ports[0].connector_list[0].plug_type == "J1772"
    assert info.station_price.tou_fees[0].fee.amount == 0.10
    assert info.station_price.guest_fee.amount == 0.99
    assert info.station_price.taxes[0].name == "State Tax"
    assert info.last_charged_date == "2026-01-01"


async def test_client_get_station_failure(
    aioresponses, authenticated_client: ChargePoint
):
    aioresponses.get(
        authenticated_client.global_config.endpoints.mapcache_endpoint
        / "v3/station/info"
        % {"deviceId": "99991111", "use_cache": "false"},
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_station(99991111)

    assert exc.value.response.status == 500


async def test_client_get_nearby_stations(
    aioresponses, authenticated_client: ChargePoint, nearby_stations_json: dict
):
    from python_chargepoint.global_config import ZoomBounds

    aioresponses.post(
        authenticated_client.global_config.endpoints.mapcache_endpoint / "v2",
        status=200,
        payload=nearby_stations_json,
    )
    bounds = ZoomBounds(sw_lat=0.0, sw_lon=0.0, ne_lat=1.0, ne_lon=1.0)
    stations = await authenticated_client.get_nearby_stations(bounds)

    assert len(stations) == 2
    public = stations[0]
    assert public.device_id == 99991111
    assert public.station_status == "available"
    assert public.is_home is False
    assert len(public.ports) == 1
    assert public.ports[0].available_power == 7.2
    home = stations[1]
    assert home.is_home is True
    assert home.charging_status == "fully_charged"
    assert home.charging_info.session_id == 1000000001
    assert home.charging_info.vehicle_info.make == "TestMake"


async def test_client_get_nearby_stations_with_filter(
    aioresponses, authenticated_client: ChargePoint, nearby_stations_json: dict
):
    from python_chargepoint.global_config import ZoomBounds
    from python_chargepoint.types import MapFilter

    aioresponses.post(
        authenticated_client.global_config.endpoints.mapcache_endpoint / "v2",
        status=200,
        payload=nearby_stations_json,
    )
    bounds = ZoomBounds(sw_lat=0.0, sw_lon=0.0, ne_lat=1.0, ne_lon=1.0)
    f = MapFilter(connector_l2=True, connector_combo=True)
    stations = await authenticated_client.get_nearby_stations(bounds, station_filter=f)

    assert len(stations) == 2


async def test_client_get_nearby_stations_failure(
    aioresponses, authenticated_client: ChargePoint
):
    from python_chargepoint.global_config import ZoomBounds

    aioresponses.post(
        authenticated_client.global_config.endpoints.mapcache_endpoint / "v2",
        status=500,
    )
    bounds = ZoomBounds(sw_lat=0.0, sw_lon=0.0, ne_lat=1.0, ne_lon=1.0)

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_nearby_stations(bounds)

    assert exc.value.response.status == 500


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

    new = await authenticated_client.start_charging_session(device_id=1)
    assert new.session_id == 1
    assert "Successfully confirmed start command." in caplog.text


# ---------------------------------------------------------------------------
# Additional coverage: get_charging_sessions, close, session property
# ---------------------------------------------------------------------------


async def test_client_get_charging_sessions(
    aioresponses, authenticated_client: ChargePoint
):
    """get_charging_sessions should parse the sessions list and populate session objects."""
    sessions_payload = {
        "sessions": [
            {
                "sessionId": 11111,
                "deviceId": 99990001,
                "deviceName": "Home Flex",
                "chargingState": "done",
                "startTimeUTC": 1743000000000,
                "energyKwh": 42.5,
                "milesAdded": 142.0,
                "totalAmount": 12.34,
                "currencyIsoCode": "USD",
            },
            {
                "sessionId": 22222,
                "deviceId": 99990002,
                "deviceName": "Work Charger",
                "chargingState": "in_progress",
                "startTimeUTC": 1743100000000,
                "energyKwh": 10.2,
                "milesAdded": 34.0,
                "totalAmount": 2.88,
                "currencyIsoCode": "USD",
            },
        ]
    }
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions",
        status=200,
        payload=sessions_payload,
    )

    sessions = await authenticated_client.get_charging_sessions(limit=5)

    assert len(sessions) == 2
    assert sessions[0].session_id == 11111
    assert sessions[0].device_id == 99990001
    assert sessions[0].device_name == "Home Flex"
    assert sessions[0].charging_state == "done"
    assert sessions[0].energy_kwh == 42.5
    assert sessions[0].miles_added == 142.0
    assert sessions[0].total_amount == 12.34
    assert sessions[0].currency_iso_code == "USD"
    assert sessions[0].start_time is not None

    assert sessions[1].session_id == 22222
    assert sessions[1].charging_state == "in_progress"


async def test_client_get_charging_sessions_empty(
    aioresponses, authenticated_client: ChargePoint
):
    """get_charging_sessions should return an empty list when no sessions exist."""
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions",
        status=200,
        payload={"sessions": []},
    )

    sessions = await authenticated_client.get_charging_sessions(limit=5)
    assert sessions == []


async def test_client_get_charging_sessions_failure(
    aioresponses, authenticated_client: ChargePoint
):
    """get_charging_sessions should raise CommunicationError on HTTP error."""
    aioresponses.post(
        authenticated_client.global_config.endpoints.internal_api_gateway_endpoint
        / "driver-bff/v1/sessions",
        status=500,
    )

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_charging_sessions(limit=5)

    assert exc.value.response.status == 500


async def test_client_close(aioresponses, authenticated_client: ChargePoint):
    """close() should close the session when the client owns it."""
    # The authenticated_client fixture creates its own session (owns_session=True)
    # close() should not raise
    await authenticated_client.close()


async def test_client_session_property(aioresponses, authenticated_client: ChargePoint):
    """session property should return the underlying aiohttp ClientSession."""
    sess = authenticated_client.session
    assert sess is not None
    # After close, accessing session is undefined behaviour but we just test the property
    assert hasattr(sess, "close")


async def test_client_pass_session_to_constructor(aioresponses, global_config_json):
    """ChargePoint.__init__ should use the passed session instead of creating one."""
    import aiohttp

    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)

    external_session = aiohttp.ClientSession()
    try:
        aioresponses.get(
            "https://account.chargepoint.com/account/v1/driver/profile/user",
            status=200,
            payload={
                "user": {
                    "email": "test@pytest.com",
                    "evatarUrl": "https://pytest.com",
                    "familyName": "Test",
                    "fullName": "Test User",
                    "givenName": "Test",
                    "phone": "1234567890",
                    "phoneCountryId": 1,
                    "userId": 1,
                    "username": "test",
                },
                "accountBalance": {
                    "accountNumber": "1",
                    "accountState": "test",
                    "balance": {"amount": "0.0", "currency": "USD"},
                },
            },
        )

        client = await ChargePoint.create(
            "test",
            coulomb_token="rAnDomBaSe64EnCodEdDaTaToKeNrAnDomBaSe64EnCodEdD#D???????#RNA-US",
            session=external_session,
        )

        # The client should use the passed session, not create a new one
        assert client.session is external_session
        await client.close()
        # External session should NOT be closed by client.close() since it doesn't own it
        # (It was already open; we just check the client doesn't crash)
    finally:
        # Clean up: external session is still open here since client doesn't own it
        await external_session.close()


async def test_client_set_coulomb_token_empty():
    """_set_coulomb_token should raise ValueError when given an empty token."""
    client = ChargePoint(username="test")
    with pytest.raises(ValueError, match="empty session token"):
        client._set_coulomb_token("")


async def test_login_password_403_non_json(
    aioresponses, global_config_json: dict, global_config: GlobalConfiguration
):
    """login_with_password should handle a 403 with non-JSON body gracefully.

    When response.json() raises, the 403 still raises LoginError via
    CommunicationError wrapping.
    """
    aioresponses.post(DISCOVERY_API, status=200, payload=global_config_json)
    aioresponses.post(
        f"{global_config.endpoints.sso_endpoint}v1/user/login",
        status=403,
        body="Service Unavailable",
    )

    client = await ChargePoint.create("test")
    with pytest.raises(LoginError) as exc:
        await client.login_with_password("demo")

    # The except Exception: pass was hit (non-JSON body), then LoginError was raised
    assert "Failed to authenticate" in str(exc.value)


async def test_request_403_non_json(
    aioresponses, authenticated_client: ChargePoint
):
    """_request should handle a 403 with non-JSON body gracefully (Datadome try/except)."""
    from python_chargepoint.global_config import ZoomBounds

    aioresponses.post(
        authenticated_client.global_config.endpoints.mapcache_endpoint / "v2",
        status=403,
        body="Gateway Timeout",
    )
    bounds = ZoomBounds(sw_lat=0.0, sw_lon=0.0, ne_lat=1.0, ne_lon=1.0)

    with pytest.raises(CommunicationError) as exc:
        await authenticated_client.get_nearby_stations(bounds)

    # Should fall through to FORBIDDEN error (except Exception: pass is hit)
    assert "FORBIDDEN" in str(exc.value)

