"""应用鉴权：存储启动令牌并提供校验。"""

import hmac

APP_TOKEN = ""


def set_token(token: str) -> None:
    global APP_TOKEN
    APP_TOKEN = token


def verify_token(x_app_token: str | None) -> None:
    if not APP_TOKEN or not x_app_token or not hmac.compare_digest(APP_TOKEN, x_app_token):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Unauthorized")
