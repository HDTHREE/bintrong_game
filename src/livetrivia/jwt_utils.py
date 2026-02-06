import jwt
from datetime import datetime, timedelta, timezone
import uuid
import typing_extensions as tp
import logging

from livetrivia.utils import getenvs

logger: logging.Logger = logging.Logger(__name__)
"""Logger for jwt module to log failures to."""


SECRET_KEY, ALGORITHM = getenvs(logger=logger)
"""Secret and algorithm to use for input to `jwt.encode`.header|.algorithm respectively."""


ACCESS_TOKEN_EXPIRE_MINUTES: int = getenvs(logger=logger)
"""Number of minutes to issue a session before it expires (access expire)."""


REFRESH_TOKEN_EXPIRE_DAYS: int = getenvs(logger=logger)
"""Number of days to issue a session before it expires (refresh expire)."""


def create_access_token(
    user_id: uuid.UUID, expires_delta: timedelta | None = None
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
    user_id: uuid.UUID, expires_delta: timedelta | None = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(
    token: str,
    token_type: tp.Literal["access", "refresh"] | None = None,
    strict: bool = True,
) -> uuid.UUID | None:
    """Verify a JWT token and return the user_id if valid.

    Args:
        token: The JWT token to verify.
        token_type: Optional token type to verify against ("access" or "refresh"), if `None` unchecked.

    Returns:
        user_id if valid, None otherwise.
    """
    try:
        payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        if token_type and payload.get("type") != token_type:
            if strict:
                raise jwt.MissingRequiredClaimError(f"type == {token_type}")
            return None

        return uuid.UUID(user_id)
    except jwt.PyJWTError:
        if strict:
            raise


def get_token_expiry(token: str, strict: bool = True) -> datetime | None:
    """Get the expiry time of a token."""
    try:
        payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if (fail := exp is None) and strict:
            raise jwt.MissingRequiredClaimError("exp")
        if fail:
            return None
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except jwt.PyJWTError:
        if strict:
            raise
