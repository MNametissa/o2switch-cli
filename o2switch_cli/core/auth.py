from __future__ import annotations

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


def auth_header(user: str, token: SecretStr) -> dict[str, str]:
    return {"Authorization": f"cpanel {user}:{token.get_secret_value()}"}
