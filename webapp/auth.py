import hashlib
import hmac
import time

from fastapi import Request

from webapp.settings import SESSION_TTL_SECONDS, env

COOKIE_NAME = "documaster_session"


class NotAuthenticated(Exception):
    pass


def _sign(value: str) -> str:
    return hmac.new(env("SESSION_SECRET").encode(), value.encode(), hashlib.sha256).hexdigest()


def check_password(candidate: str) -> bool:
    return hmac.compare_digest(candidate.encode(), env("APP_PASSWORD").encode())


def create_token() -> str:
    expires = str(int(time.time()) + SESSION_TTL_SECONDS)
    return f"{expires}.{_sign(expires)}"


def is_valid_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    expires, signature = token.split(".", 1)
    if not hmac.compare_digest(signature, _sign(expires)):
        return False
    return expires.isdigit() and int(expires) > time.time()


def require_login(request: Request) -> None:
    if not is_valid_token(request.cookies.get(COOKIE_NAME)):
        raise NotAuthenticated()
