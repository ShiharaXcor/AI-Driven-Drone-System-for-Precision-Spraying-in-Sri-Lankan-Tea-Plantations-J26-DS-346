import base64
import hashlib
import hmac
import json
import time
from fastapi import Header, HTTPException
from . import config


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload):
    return _b64(hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest())


def make_token(user, ttl=None):
    ttl = config.TOKEN_TTL_S if ttl is None else ttl
    payload = _b64(json.dumps({"u": user, "exp": int(time.time()) + ttl}).encode())
    return f"{payload}.{_sign(payload)}"


def verify_token(token):
    try:
        payload, sig = token.split(".", 1)
        if not hmac.compare_digest(sig.encode(), _sign(payload).encode()):
            return None
        data = json.loads(_unb64(payload))
        return data["u"] if data["exp"] >= time.time() else None
    except Exception:
        return None


def is_authorized(x_api_key="", authorization=""):
    if x_api_key and hmac.compare_digest(x_api_key.encode(), config.API_KEY.encode()):
        return True
    if authorization.lower().startswith("bearer "):
        return verify_token(authorization[7:].strip()) is not None
    return False


def require_key(x_api_key: str = Header(default=""), authorization: str = Header(default="")):
    if not is_authorized(x_api_key, authorization):
        raise HTTPException(401, "Invalid or missing credentials")