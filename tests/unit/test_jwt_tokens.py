import uuid

import jwt

from livetrivia.jwt_utils import (
    create_access_token,
    create_refresh_token,
    get_token_expiry,
    verify_token,
)


def test_access_token_round_trip() -> None:
    user_id = uuid.uuid4()
    access_token = create_access_token(user_id)

    verified_user_id = verify_token(access_token, token_type="access")

    assert verified_user_id == user_id
    assert get_token_expiry(access_token) is not None


def test_refresh_token_round_trip() -> None:
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(user_id)

    verified_user_id = verify_token(refresh_token, token_type="refresh")

    assert verified_user_id == user_id
    assert get_token_expiry(refresh_token) is not None


def test_access_token_rejected_as_refresh() -> None:
    user_id = uuid.uuid4()
    access_token = create_access_token(user_id)

    assert verify_token(access_token, token_type="refresh", strict=False) is None

    try:
        verify_token(access_token, token_type="refresh")
    except jwt.MissingRequiredClaimError as error:
        assert "type == refresh" in str(error)
    else:
        raise AssertionError(
            "Expected MissingRequiredClaimError for token type mismatch"
        )


def test_refresh_token_rejected_as_access() -> None:
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(user_id)

    assert verify_token(refresh_token, token_type="access", strict=False) is None

    try:
        verify_token(refresh_token, token_type="access")
    except jwt.MissingRequiredClaimError as error:
        assert "type == access" in str(error)
    else:
        raise AssertionError(
            "Expected MissingRequiredClaimError for token type mismatch"
        )
