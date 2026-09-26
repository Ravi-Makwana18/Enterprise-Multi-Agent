import hmac
import os
from typing import Any

from fastapi import Depends, HTTPException, Request

from backend.config import settings


_DEMO_TOKENS = {
    "user-demo-token": "user",
    "admin-demo-token": "admin",
}


def _parse_tokens(raw_tokens: str | None) -> dict[str, str]:
    tokens: dict[str, str] = {}
    if not raw_tokens:
        return tokens

    for item in raw_tokens.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        token, role = item.split(":", 1)
        token = token.strip()
        role = role.strip().lower()
        if token and role:
            tokens[token] = role
    return tokens


def get_known_tokens() -> dict[str, str]:
    tokens = _parse_tokens(settings.api_tokens)
    if settings.allow_demo_auth:
        tokens.update(_DEMO_TOKENS)
    return tokens


def get_token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    return None


def authenticate_token(token: str | None) -> dict[str, str] | None:
    if not token:
        return None

    for known_token, role in get_known_tokens().items():
        if hmac.compare_digest(token, known_token):
            return {"token": token, "role": role, "username": f"{role}-user"}
    return None


async def get_current_user(request: Request) -> dict[str, str]:
    token = get_token_from_request(request)
    user = authenticate_token(token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "authentication_required", "message": "Valid API token required."}},
        )
    return user


def require_roles(*allowed_roles: str):
    async def dependency(user: dict[str, str] = Depends(get_current_user)) -> dict[str, str]:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "forbidden", "message": f"Role required: {', '.join(allowed_roles)}"}},
            )
        return user

    return dependency
