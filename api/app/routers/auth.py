from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models import Language, User, UserType
from app.schemas import (
    InterestsIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UserOut,
)
from app.security import (
    CurrentUser,
    DbSession,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: DbSession) -> TokenPair:
    existing = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        preferred_language=Language(payload.preferred_language),
        user_type=UserType(payload.user_type),
        interests={},
    )
    db.add(user)
    db.commit()
    return TokenPair(
        access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id)
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginIn, db: DbSession) -> TokenPair:
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    # Same message either way: never reveal whether an address is registered.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenPair(
        access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id)
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshIn, db: DbSession) -> TokenPair:
    user_id = decode_token(payload.refresh_token, expected_kind="refresh")
    if db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return TokenPair(
        access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id)
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.put("/me/interests", response_model=UserOut)
def set_interests(payload: InterestsIn, user: CurrentUser, db: DbSession) -> UserOut:
    user.interests = payload.interests
    db.add(user)
    db.commit()
    return UserOut.model_validate(user)
