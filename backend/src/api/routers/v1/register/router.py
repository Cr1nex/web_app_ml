from fastapi import APIRouter, Depends, Request, Response, status

from core.db.session import get_db
from core.rate_limit import limiter
from core.utils.cookies import set_auth_cookies
from core.utils.deps import get_redis
from models.user import RegistrationResponse, UserCreate
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_service(db=Depends(get_db), redis_client=Depends(get_redis)):
    return UserService(db, redis_client)


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def register_user(
    request: Request,
    response: Response,
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
):
    result = service.register(payload)
    set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        username=result.user.username,
        access_ttl=result.tokens.expires_in,
    )
    return result
