"""Platform sign-up and sign-in — our customers' accounts.

Email and password, because it works with no third-party setup. `oauth_provider`
on the user row is the seam for adding Google sign-in later without touching
anything else.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.deps import CurrentUser, SessionDep
from app.models import User
from app.security import (
    create_platform_token,
    hash_password,
    password_problem,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


def _user_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, session: SessionDep) -> AuthResponse:
    problem = password_problem(body.password)
    if problem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    email = body.email.strip().lower()
    existing = session.scalars(
        select(User).where(func.lower(User.email) == email)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists. Try signing in.",
        )

    user = User(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
    )
    session.add(user)
    session.commit()

    return AuthResponse(token=create_platform_token(user.id, user.email), user=_user_payload(user))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, session: SessionDep) -> AuthResponse:
    email = body.email.strip().lower()
    user = session.scalars(select(User).where(func.lower(User.email) == email)).first()

    # One message for both a wrong address and a wrong password, so the API
    # does not reveal which addresses have accounts.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password do not match.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active."
        )

    return AuthResponse(token=create_platform_token(user.id, user.email), user=_user_payload(user))


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return _user_payload(user)
