import asyncio
import aiohttp
import dash
import dash.exceptions as de
import dash_mantine_components as dmc
from livetrivia.models.user import LoginRequest
from livetrivia.utils import getenvs, getmod
from livetrivia._fe_app.components import token_store, user_store

app: dash.Dash = dash.get_app()


BACKEND_URL: str = getenvs()


email_input = dmc.TextInput(
    placeholder="user@example.com",
    label="Email",
    size="md",
    required=True,
)

password_input = dmc.PasswordInput(label="Password", size="md", required=True)


confirm_input = dmc.PasswordInput(label="Confirm", size="md", required=True)


login_button = dmc.Button("Login")


new_button = dmc.Button("New?")


create_button = dmc.Button("Create")


back_button = dmc.Button("Back")


login_collapse = dmc.Collapse(
    children=dmc.Flex([login_button, dmc.Space(w=10), new_button]),
    keepMounted=True,
    opened=True,
)


create_collapse = dmc.Collapse(
    children=dmc.Stack(
        [confirm_input, dmc.Flex([create_button, dmc.Space(w=10), back_button])],
        w="100%",
    ),
    keepMounted=True,
)


login = dmc.Center(
    dmc.Card(
        w="60vw",
        children=dmc.Fieldset(
            children=[
                email_input,
                dmc.Space(h=10),
                password_input,
                dmc.Space(h=10),
                login_collapse,
                create_collapse,
            ],
            flex="column",
        ),
    )
)




@app.callback(
    dash.Output(token_store, "data", allow_duplicate=True),
    dash.Output(user_store, "data", allow_duplicate=True),
    dash.Input(login_button, "n_clicks"),
    dash.State(email_input, "value"),
    dash.State(password_input, "value"),
    prevent_initial_call=True,
)
async def on_login(_: int, email: str | None, password: str | None):
    if not email or not password:
        raise de.PreventUpdate()
    user: LoginRequest = LoginRequest(email=email, password=password)
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.post("api/sessions/login", json=user.model_dump()) as session_response,
    ):
        return await session_response.json(), email


@app.callback(
    dash.Output(token_store, "data", allow_duplicate=True),
    dash.Output(user_store, "data", allow_duplicate=True),
    dash.Input(create_button, "n_clicks"),
    dash.State(email_input, "value"),
    dash.State(password_input, "value"),
    prevent_initial_call=True,
)
async def on_signup(_: int, email: str | None, password: str | None):
    if not email or not password:
        raise de.PreventUpdate()
    user: LoginRequest = LoginRequest(email=email, password=password)
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.post("api/users", json=user.model_dump()) as session_response,
    ):
        async with session.post(
            "api/sessions/login", json=user.model_dump()
        ) as login_response:
            *_, token = await asyncio.gather(session_response.json(), login_response.json())
    return token, email


app.clientside_callback(
    dash.ClientsideFunction("login", "updateCurrentMenu"),
    dash.Output(login_collapse, "opened"),
    dash.Output(create_collapse, "opened"),
    dash.Input(new_button, "n_clicks"),
    dash.Input(back_button, "n_clicks"),
)


app.clientside_callback(
    dash.ClientsideFunction("login", "updateStateLogin"),
    dash.Output(login_button, "disabled"),
    dash.Input(email_input, "value"),
    dash.Input(password_input, "value"),
    prevent_initial_call=True
)


app.clientside_callback(
    dash.ClientsideFunction("login", "updateStateCreate"),
    dash.Output(create_button, "disabled"),
    dash.Input(email_input, "value"),
    dash.Input(password_input, "value"),
    dash.Input(confirm_input, "value"),
    prevent_initial_call=True
)


layout: dmc.AppShellMain = dmc.AppShellMain(children=login)


dash.register_page(
    getmod(__name__),
    path="/login",
    layout=layout,
)
