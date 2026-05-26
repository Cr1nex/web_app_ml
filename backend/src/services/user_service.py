from fastapi import HTTPException, status

from core.utils.hashing import hash_password, verify_password
from models.user import LoginResponse, RegistrationResponse, UserCreate, UserOut
from repos.user_repo import UserRepo
from services.token_service import TokenService


class UserService:
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.user_repo = UserRepo(db)
        self.token_service = TokenService(db, redis_client)

    def register(self, payload: UserCreate) -> RegistrationResponse:
        if self.user_repo.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_in_use")
        if self.user_repo.get_by_username(payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username_in_use")

        user = self.user_repo.create(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
        )
        tokens = self.token_service.issue_token_pair(user.user_id)

        return RegistrationResponse(user=UserOut.model_validate(user), tokens=tokens)

    def login(self, email: str, password: str) -> LoginResponse:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

        tokens = self.token_service.issue_token_pair(user.user_id)
        return LoginResponse(user=UserOut.model_validate(user), tokens=tokens)
