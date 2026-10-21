import hmac
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import config
from ..auth import make_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn):
    ok_user = hmac.compare_digest(body.username.encode(), config.ADMIN_USER.encode())
    ok_pass = hmac.compare_digest(body.password.encode(), config.ADMIN_PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(401, "Wrong username or password")
    return {"token": make_token(body.username), "expires_in": config.TOKEN_TTL_S}