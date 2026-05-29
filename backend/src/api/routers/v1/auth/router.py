from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from core.db.session import get_db
from core.rate_limit import limiter
from core.security.jwks import get_cached_jwks
from core.utils.cookies import clear_auth_cookies, set_auth_cookies
from core.utils.deps import get_current_user_id, get_redis
from models.token import TokenPair
from models.user import LoginResponse
from services.user_service import UserService
from services.token_service import TokenService
from api.routers.v1.auth.schemas import LoginRequest, RefreshRequest

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_TTL = 60 * 60 * 24 * 7


def get_user_service(db=Depends(get_db), redis_client=Depends(get_redis)):
    return UserService(db, redis_client)


@router.get("/jwks")
@limiter.limit("120/minute")
def jwks(request: Request, redis_client=Depends(get_redis)):
    return get_cached_jwks(redis_client)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    service: UserService = Depends(get_user_service),
):
    result = service.login(email=str(payload.email), password=payload.password)
    set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        username=result.user.username,
        access_ttl=result.tokens.expires_in,
    )
    return result


@router.post("/refresh", response_model=TokenPair)
@limiter.limit("30/minute")
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest,
    db=Depends(get_db),
    redis_client=Depends(get_redis),
):
    # Cookie (web) takes priority; body (mobile) is the fallback.
    # Schema accepts an empty body so cookie-only web clients pass Pydantic;
    # we enforce "must have one" here at the application layer.
    refresh_tok = request.cookies.get("refresh_token") or payload.refresh_token
    if not refresh_tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_refresh_token",
        )
    token_service = TokenService(db, redis_client)
    new_pair = token_service.rotate_refresh_token(refresh_tok)
    # Rotate the token cookies; username cookie stays valid
    common = dict(samesite="lax", secure=False, path="/")
    response.set_cookie("access_token",  new_pair.access_token,  httponly=True, max_age=new_pair.expires_in, **common)
    response.set_cookie("refresh_token", new_pair.refresh_token, httponly=True, max_age=_REFRESH_TTL,        **common)
    return new_pair


@router.post("/logout", status_code=200)
def logout(response: Response):
    clear_auth_cookies(response)
    return {"logged_out": True}


@router.get("/check")
@limiter.limit("120/minute")
def check_session(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
):
    """Returns 200 if the access_token cookie is still valid, 401 otherwise.

    Cheap probe the frontend uses on page reload before deciding whether
    to call /refresh — no token rotation, no DB write.
    """
    return {"user_id": str(user_id)}
