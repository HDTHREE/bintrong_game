from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
import sqlalchemy.ext.asyncio as sqlas
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

from livetrivia.models.user import User
from livetrivia.models.session import Session
from livetrivia.db import get_async_session
from livetrivia.routes.user import verify_password
from livetrivia.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_expiry,
)

router: APIRouter = APIRouter(prefix="/sessions", tags=["sessions"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Login a user and create 2 JWT session tokens."""
    stmt = select(User).where(User.email == login_data.email)
    result = await session.execute(stmt)
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
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    refresh_token: str,
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Refresh the access token using a valid refresh token."""
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
    result = await session.execute(stmt)
    db_session = result.scalars().first()

    if not db_session:
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

    db_session.access_token = new_access_token
    db_session.access_token_expires_at = access_token_expires_at
    session.add(db_session)
    await session.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=db_session.refresh_token_expires_at,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    access_token: str,
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> dict:
    """Disables a session. Sets flag to false."""
    user_id = verify_token(access_token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.user_id == user_id)
    )
    result = await session.execute(stmt)
    db_session = result.scalars().first()

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    db_session.is_active = False
    session.add(db_session)
    await session.commit()

    return {"message": "Logged out successfully"}


@router.get("/", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_current_session(
    access_token: str,
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> Session:
    """Get current session information."""
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
    result = await session.execute(stmt)
    db_session = result.scalars().first()

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )

    return db_session


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    access_token: str,
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a session record."""
    user_id = verify_token(access_token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.user_id == user_id)
    )
    result = await session.execute(stmt)
    db_session = result.scalars().first()

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    await session.delete(db_session)
    await session.commit()
