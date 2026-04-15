from __future__ import annotations

import json
from typing import Any

import httpx

from o2switch_cli.config.settings import AppSettings
from o2switch_cli.core.auth import auth_header
from o2switch_cli.core.errors import AuthAppError, PermissionAppError, TransportAppError
from o2switch_cli.core.models import ApiResult


class CpanelClient:
    def __init__(self, settings: AppSettings, client: httpx.Client | None = None) -> None:
        if not settings.cpanel_user:
            raise AuthAppError("cpanel_client_init", "cpanel_user is required but not configured.")
        self._settings = settings
        use_basic = settings.auth_method == "password"
        headers = {
            **auth_header(settings.cpanel_user, settings.cpanel_token, use_basic=use_basic),  # type: ignore[arg-type]
            "User-Agent": "o2switch-cli/0.1.3",
            "Accept": "application/json",
        }
        self._client = client or httpx.Client(
            base_url=f"https://{settings.cpanel_host}:{settings.port}",
            headers=headers,
            timeout=settings.timeout_seconds,
            follow_redirects=True,
        )
        self._client.headers.update(headers)

    @classmethod
    def from_settings(cls, settings: AppSettings) -> CpanelClient:
        return cls(settings=settings)

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, *, params: Any | None = None) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, params=params)
        except httpx.HTTPError as exc:
            raise TransportAppError("cpanel_request", str(exc)) from exc
        if response.status_code == 401:
            raise AuthAppError("cpanel_request", "cPanel rejected the API token or credentials.")
        if response.status_code == 403:
            raise PermissionAppError("cpanel_request")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TransportAppError("cpanel_request", f"Unexpected HTTP status {response.status_code}.") from exc
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise TransportAppError("cpanel_request", "cPanel returned invalid JSON.") from exc

    def _parse_uapi(self, payload: dict[str, Any], operation: str) -> ApiResult:
        result = payload.get("result", payload)
        status = result.get("status", payload.get("status", 1))
        if status not in (1, "1"):
            errors = result.get("errors") or payload.get("errors") or []
            detail = errors[0] if errors else f"{operation} failed."
            raise TransportAppError(operation, detail)
        return ApiResult(
            data=result.get("data", payload.get("data")),
            metadata=result.get("metadata", payload.get("metadata", {})) or {},
            warnings=result.get("warnings", payload.get("warnings", [])) or [],
            messages=result.get("messages", payload.get("messages", [])) or [],
        )

    def _parse_api2(self, payload: dict[str, Any], operation: str) -> ApiResult:
        result = payload.get("cpanelresult", payload)
        event = result.get("event", {})
        if event and event.get("result") not in (1, "1"):
            raise TransportAppError(operation, event.get("reason", f"{operation} failed."))
        data = result.get("data")
        if isinstance(data, dict):
            detail = self._api2_failure_detail(data, operation)
            if detail:
                raise TransportAppError(operation, detail)
        elif isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                detail = self._api2_failure_detail(item, operation)
                if detail:
                    raise TransportAppError(operation, detail)
        return ApiResult(
            data=data,
            metadata=result.get("metadata", {}) or {},
            warnings=result.get("warnings", []) or [],
            messages=result.get("messages", []) or [],
        )

    @staticmethod
    def _api2_failure_detail(payload: dict[str, Any], operation: str) -> str | None:
        if "result" not in payload:
            return None
        if payload.get("result") in (1, "1", True):
            return None
        detail = payload.get("reason") or payload.get("statusmsg") or payload.get("error") or f"{operation} failed."
        return str(detail)

    def uapi(self, module: str, function: str, **params: Any) -> ApiResult:
        payload = self._request("GET", f"/execute/{module}/{function}", params=params)
        return self._parse_uapi(payload, f"{module}/{function}")

    def api2(self, module: str, function: str, **params: Any) -> ApiResult:
        payload = self._request(
            "GET",
            "/json-api/cpanel",
            params={
                "cpanel_jsonapi_user": self._settings.cpanel_user,
                "cpanel_jsonapi_apiversion": 2,
                "cpanel_jsonapi_module": module,
                "cpanel_jsonapi_func": function,
                **params,
            },
        )
        return self._parse_api2(payload, f"{module}::{function}")

    def list_domains(self) -> ApiResult:
        return self.uapi("DomainInfo", "list_domains", hide_temporary_domains=1)

    def parse_zone(self, zone: str) -> ApiResult:
        return self.uapi("DNS", "parse_zone", zone=zone)

    def mass_edit_zone(
        self,
        *,
        zone: str,
        serial: int | None = None,
        add: list[dict[str, Any]] | None = None,
        edit: list[dict[str, Any]] | None = None,
        remove: list[int] | None = None,
    ) -> ApiResult:
        params: list[tuple[str, str | int]] = [("zone", zone)]
        if serial is not None:
            params.append(("serial", serial))
        for key, values in (("add", add or []), ("edit", edit or [])):
            for value in values:
                params.append((key, json.dumps(value)))
        for line_index in remove or []:
            params.append(("remove", line_index))
        payload = self._request("GET", "/execute/DNS/mass_edit_zone", params=params)
        return self._parse_uapi(payload, "DNS/mass_edit_zone")

    def add_subdomain(self, *, domain: str, rootdomain: str, directory: str) -> ApiResult:
        return self.uapi("SubDomain", "addsubdomain", domain=domain, rootdomain=rootdomain, dir=directory)

    def list_subdomains(self) -> ApiResult:
        return self.api2("SubDomain", "listsubdomains")

    def delete_subdomain(self, *, domain: str) -> ApiResult:
        return self.api2("SubDomain", "delsubdomain", domain=domain)

    def test_access(self) -> ApiResult:
        return self.list_domains()
