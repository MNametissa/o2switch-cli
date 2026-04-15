from __future__ import annotations

import base64

import questionary
from pydantic import SecretStr

from o2switch_cli.config.settings import AppSettings
from o2switch_cli.core.errors import AuthAppError


def ensure_credentials(settings: AppSettings, *, allow_prompt: bool) -> AppSettings:
    updates: dict[str, object] = {}
    if allow_prompt:
        if not settings.cpanel_host:
            updates["cpanel_host"] = questionary.text("cPanel host").ask()
        if not settings.cpanel_user:
            updates["cpanel_user"] = questionary.text("cPanel user").ask()
        if not settings.cpanel_token:
            token = questionary.password("cPanel API token").ask()
            if token:
                updates["cpanel_token"] = SecretStr(token)
    merged = settings.model_copy(update=updates)
    if not merged.cpanel_host or not merged.cpanel_user or not merged.cpanel_token:
        raise AuthAppError("auth")
    return merged


def auth_header(user: str, token: SecretStr, *, use_basic: bool = False) -> dict[str, str]:
    """Generate auth header. use_basic=True for password auth."""
    secret = token.get_secret_value()
    if use_basic:
        encoded = base64.b64encode(f"{user}:{secret}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    return {"Authorization": f"cpanel {user}:{secret}"}
