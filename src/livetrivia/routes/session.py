import typing_extensions as tp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from pydantic import BaseModel
from datetime import datetime
import uuid

from livetrivia.models.user import User, LoginRequest
from livetrivia.models.session import Session
from livetrivia.db import SqlSession
from livetrivia.routes.user import verify_password
from livetrivia.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_expiry,
)

router: APIRouter = APIRouter(prefix="/sessions", tags=["sessions"])


BearerCredentials: tp.TypeAlias = tp.Annotated[
    HTTPAuthorizationCredentials, Depends(HTTPBearer())
]


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    access_token: str
    refresh_token: str
    created_at: datetime
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime

    class Config:
        from_attributes = True


@router.post(
    "/guest", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def create_guest_session(
    sql: SqlSession,
) -> TokenResponse:
    # Create a temporary guest id that doens't actually get committed to the database.
    guest_id: uuid.UUID = uuid.uuid4()

    access_token = create_access_token(guest_id)
    refresh_token = create_refresh_token(guest_id)

    access_token_expires_at = get_token_expiry(access_token)
    refresh_token_expires_at = get_token_expiry(refresh_token)

    if access_token_expires_at is None or refresh_token_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tokens",
        )

    new_session = Session(
        user_id=None,  # (i.e. this is `None`.)
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
    )
    sql.add(new_session)
    await sql.commit()
    await sql.refresh(new_session)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    sql: SqlSession,
) -> TokenResponse:
    """Login a user and create 2 JWT session tokens."""
    stmt = select(User).where(User.email == login_data.email)
    result = await sql.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    access_token_expires_at = get_token_expiry(access_token)
    refresh_token_expires_at = get_token_expiry(refresh_token)

    if access_token_expires_at is None or refresh_token_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tokens",
        )

    new_session = Session(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
    )
    sql.add(new_session)
    await sql.commit()
    await sql.refresh(new_session)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    credentials: BearerCredentials,
    sql: SqlSession,
) -> TokenResponse:
    """Refresh the access token using a valid refresh token."""
    refresh_token = credentials.credentials
    user_id = verify_token(refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    stmt = select(Session).where(
        (Session.refresh_token == refresh_token)
        & (Session.user_id == user_id)
        & (Session.is_active)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )

    new_access_token = create_access_token(user_id)
    access_token_expires_at = get_token_expiry(new_access_token)

    if access_token_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate new access token",
        )

    session.access_token = new_access_token
    session.access_token_expires_at = access_token_expires_at
    sql.add(session)
    await sql.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=session.refresh_token_expires_at,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: BearerCredentials,
    sql: SqlSession,
) -> dict:
    """Disables a session. Sets flag to false."""
    access_token = credentials.credentials
    user_id = verify_token(access_token, token_type="access", strict=False)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.user_id == user_id)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session.is_active = False
    sql.add(session)
    await sql.commit()

    return {"message": "Logged out successfully"}


@router.get("/", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_current_session(
    credentials: BearerCredentials,
    sql: SqlSession,
) -> Session:
    """Get current session information."""
    access_token = credentials.credentials
    user_id = verify_token(access_token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token)
        & (Session.user_id == user_id)
        & (Session.is_active)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )

    return session


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    credentials: BearerCredentials,
    sql: SqlSession,
) -> None:
    """Delete a session record."""
    access_token = credentials.credentials
    user_id = verify_token(access_token, token_type="access", strict=False)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.user_id == user_id)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    await sql.delete(session)
    await sql.commit()


async def get_current_user(credentials: BearerCredentials) -> uuid.UUID:
    """Verify access token and return user_id."""
    access_token = credentials.credentials
    user_id: uuid.UUID | None = verify_token(
        access_token, token_type="access", strict=False
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    return user_id


CurrentUserId: tp.TypeAlias = tp.Annotated[uuid.UUID, Depends(get_current_user)]
