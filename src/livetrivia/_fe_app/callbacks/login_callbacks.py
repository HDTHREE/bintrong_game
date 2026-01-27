import aiohttp
import asyncio
import dash
import dash.exceptions as de
from livetrivia._fe_app.pages.login import (
    password_input,
    token,
    email_input,
    confirm_input,
    create_collapse,
    login_collapse,
    new_button,
    login_button,
    create_button,
    back_button,
)
from livetrivia.models.user import LoginRequest
from livetrivia.utils import getenvs

BACKEND_URL: str = getenvs()


@dash.callback(
    dash.Output(token, "data", allow_duplicate=True),
    dash.Input(login_button, "n_clicks"),
    dash.State(email_input, "value"),
    dash.State(password_input, "value"),
    prevent_initial_call=True,
)
async def on_login(_: int, email: str | None, password: str | None):
    if not email or not password:
        raise de.PreventUpdate()
    user: LoginRequest = LoginRequest(email=email, password=password)
    async with aiohttp.ClientSession(BACKEND_URL) as session, session.post("api/sessions/login", json=user.model_dump()) as response:
        return await response.json()
    
    


@dash.callback(
    dash.Output(token, "data", allow_duplicate=True),
    dash.Input(create_button, "n_clicks"),
    dash.State(email_input, "value"),
    dash.State(password_input, "value"),
    prevent_initial_call=True,
)
async def on_signup(_: int, email: str | None, password: str | None):
    if not email or not password:
        raise de.PreventUpdate()
    user: LoginRequest = LoginRequest(email=email, password=password)
    async with aiohttp.ClientSession(BACKEND_URL) as session, session.post("api/users", json=user.model_dump()) as response:
        async with session.post("api/sessions/login", json=user.model_dump()) as login_response:
            *_, token = await asyncio.gather(response.json(), login_response.json())
    return token


dash.clientside_callback(
    dash.ClientsideFunction("clientside", "onClickNew"),
    dash.Output(login_collapse, "opened", allow_duplicate=True),
    dash.Output(create_collapse, "opened", allow_duplicate=True),
    dash.Input(new_button, "n_clicks"),
    prevent_initial_call=True,
)


dash.clientside_callback(
    dash.ClientsideFunction("clientside", "updateStateLogin"),
    dash.Output(login_button, "disabled"),
    dash.Input(email_input, "value"),
    dash.Input(password_input, "value"),
)




dash.clientside_callback(
    dash.ClientsideFunction("clientside", "updateStateCreate"),
    dash.Output(create_button, "disabled"),
    dash.Input(email_input, "value"),
    dash.Input(password_input, "value"),
    dash.Input(confirm_input, "value"),
)


dash.clientside_callback(
    dash.ClientsideFunction("clientside", "onClickCancel"),
    dash.Output(login_collapse, "opened", allow_duplicate=True),
    dash.Output(create_collapse, "opened", allow_duplicate=True),
    dash.Input(back_button, "n_clicks"),
    prevent_initial_call=True,
)
