import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from livetrivia.models.user import LoginRequest, User

from livetrivia.routes.user import create_user, verify_password


@pytest.fixture
def sql_session() -> MagicMock:
    session: MagicMock = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    execute_result: MagicMock = MagicMock()
    scalars_result: MagicMock = MagicMock()
    scalars_result.first.return_value = None
    execute_result.scalars.return_value = scalars_result
    session.execute.return_value = execute_result

    return session


def test_create_user_success(sql_session: MagicMock):
    user_data = LoginRequest(email="new-user@example.com", password="my-password")

    created_user = asyncio.run(create_user(user_data=user_data, sql=sql_session))

    assert created_user.email == user_data.email
    assert created_user.password != user_data.password
    assert verify_password(user_data.password, created_user.password)
    sql_session.add.assert_called_once()
    sql_session.commit.assert_awaited_once()
    sql_session.refresh.assert_awaited_once_with(created_user)


def test_create_user_existing_email(sql_session: MagicMock):
    existing_user = User(email="existing@example.com", password="hashed")
    sql_session.execute.return_value.scalars.return_value.first.return_value = (
        existing_user
    )

    user_data = LoginRequest(email="existing@example.com", password="my-password")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(create_user(user_data=user_data, sql=sql_session))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Email already registered"
    sql_session.add.assert_not_called()
    sql_session.commit.assert_not_awaited()
    sql_session.refresh.assert_not_awaited()
