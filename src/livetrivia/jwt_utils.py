import jwt
import typing as tp
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from livetrivia.utils import getenvs


SECRET_KEY, ALGORITHM = getenvs()


ACCESS_TOKEN_EXPIRE_MINUTES: int = getenvs()


REFRESH_TOKEN_EXPIRE_DAYS: int = getenvs()


def create_access_token(
    user_id: uuid.UUID, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"sub": str(user_id), "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: uuid.UUID, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


type TokenType = tp.Literal["access", "refresh"] | None


def verify_token(token: str, token_type: Optional[str] = None) -> Optional[uuid.UUID]:
    """Verify a JWT token and return the user_id if valid.

    Args:
        token: The JWT token to verify.
        token_type: Optional token type to verify against ("access" or "refresh"), if `None` unchecked.

    Returns:
        user_id if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        if token_type and payload.get("type") != token_type:
            return None

        return uuid.UUID(user_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiry time of a token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except jwt.InvalidTokenError:
        return None


def get_token_type(token: str) -> Optional[str]:
    """Get the type of a token (access or refresh)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("type")
    except jwt.InvalidTokenError:
        return None

# TODO logging