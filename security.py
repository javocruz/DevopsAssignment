import hmac

from fastapi import Header, HTTPException

from config import get_settings


def require_admin(x_admin_token: str | None = Header(None)):
    token = get_settings().admin_token
    if token == "":
        return
    # Same time either way, so a wrong guess does not reveal how many
    # characters matched. A missing header is not a string, so skip the compare.
    if isinstance(x_admin_token, str) and hmac.compare_digest(x_admin_token, token):
        return
    raise HTTPException(status_code=401)
