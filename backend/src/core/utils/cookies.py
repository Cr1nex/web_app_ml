from fastapi import Response

_REFRESH_TTL = 60 * 60 * 24 * 7  # 7 days


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    username: str,
    access_ttl: int,
) -> None:
    """
    Set authentication cookies on a FastAPI Response.

    - access_token  : HttpOnly (JS cannot read) — sent automatically by browser
    - refresh_token : HttpOnly (JS cannot read) — sent automatically by browser
    - username      : readable by JS — used by frontend to show "logged in as …"

    Tokens are also returned in the JSON response body for mobile / API clients.
    """
    common = dict(samesite="lax", secure=False, path="/")
    response.set_cookie("access_token",  access_token,  httponly=True,  max_age=access_ttl,   **common)
    response.set_cookie("refresh_token", refresh_token, httponly=True,  max_age=_REFRESH_TTL, **common)
    response.set_cookie("username",      username,      httponly=False, max_age=_REFRESH_TTL, **common)


def clear_auth_cookies(response: Response) -> None:
    """Expire all auth cookies (called by the logout endpoint)."""
    for name in ("access_token", "refresh_token", "username"):
        response.delete_cookie(name, path="/", samesite="lax")
