from __future__ import annotations

import json

import httpx
from pydantic import SecretStr

from o2switch_cli.config.settings import AppSettings
from o2switch_cli.core.cpanel_client import CpanelClient
from o2switch_cli.core.errors import AuthAppError


def build_settings() -> AppSettings:
    return AppSettings(
        cpanel_host="cpanel.example.test",
        cpanel_user="demo",
        cpanel_token=SecretStr("secret-token"),
    )


def test_uapi_request_uses_cpanel_token_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/execute/DomainInfo/list_domains"
        assert request.headers["Authorization"] == "cpanel demo:secret-token"
        return httpx.Response(200, json={"result": {"status": 1, "data": {"main_domain": "ginutech.com"}}})

    client = httpx.Client(base_url="https://cpanel.example.test:2083", transport=httpx.MockTransport(handler))
    response = CpanelClient(build_settings(), client=client).list_domains()
    assert response.data["main_domain"] == "ginutech.com"


def test_api2_request_includes_expected_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        assert request.url.path == "/json-api/cpanel"
        assert params["cpanel_jsonapi_module"] == "SubDomain"
        assert params["cpanel_jsonapi_func"] == "listsubdomains"
        assert params["cpanel_jsonapi_apiversion"] == "2"
        return httpx.Response(
            200,
            json={"cpanelresult": {"event": {"result": 1}, "data": [{"domain": "app.ginutech.com"}]}},
        )

    client = httpx.Client(base_url="https://cpanel.example.test:2083", transport=httpx.MockTransport(handler))
    response = CpanelClient(build_settings(), client=client).list_subdomains()
    assert response.data[0]["domain"] == "app.ginutech.com"


def test_mass_edit_zone_serializes_operations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        params = list(request.url.params.multi_items())
        assert ("domain", "ginutech.com") in params
        add_payload = next(value for key, value in params if key == "add")
        assert json.loads(add_payload)["address"] == "203.0.113.25"
        return httpx.Response(200, json={"result": {"status": 1, "data": {"ok": True}}})

    client = httpx.Client(base_url="https://cpanel.example.test:2083", transport=httpx.MockTransport(handler))
    api = CpanelClient(build_settings(), client=client)
    result = api.mass_edit_zone(
        domain="ginutech.com",
        add=[{"record_type": "A", "dname": "odoo.ginutech.com", "ttl": 300, "address": "203.0.113.25"}],
    )
    assert result.data["ok"] is True



def test_uapi_401_maps_to_auth_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"status": 0})

    client = httpx.Client(base_url="https://cpanel.example.test:2083", transport=httpx.MockTransport(handler))
    api = CpanelClient(build_settings(), client=client)
    try:
        api.list_domains()
    except AuthAppError:
        return
    raise AssertionError("Expected AuthAppError")
