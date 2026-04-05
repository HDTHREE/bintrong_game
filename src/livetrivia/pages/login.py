import aiohttp
import dash
import dash.exceptions as de
import dash_mantine_components as dmc
from livetrivia.models.user import LoginRequest
from livetrivia.utils import getenvs, getmod, ClientsideFunctionType
from livetrivia.shared_components import token_store, user_store


app: dash.Dash = dash.get_app()
"""Reference to global dash object."""


BACKEND_URL: str = getenvs(logger=app.logger)
"""URL to backend service."""


layout: dmc.AppShellMain = dmc.AppShellMain(
    children=dmc.Center(
        children=dmc.Card(
            w="60vw",
            children=dmc.Fieldset(
                children=[
                    email_input := dmc.TextInput(
                        placeholder="user@example.com",
                        label="Email",
                        size="md",
                        required=True,
                    ),
                    dmc.Space(h=10),
                    password_input := dmc.PasswordInput(
                        label="Password", size="md", required=True
                    ),
                    dmc.Space(h=10),
                    login_collapse := dmc.Collapse(
                        children=dmc.Flex(
                            [
                                login_button := dmc.Button(children="Login"),
                                dmc.Space(w=10),
                                new_button := dmc.Button(
                                    children="New?", id="new-button"
                                ),
                            ]
                        ),
                        keepMounted=True,
                        opened=True,
                    ),
                    create_collapse := dmc.Collapse(
                        children=dmc.Stack(
                            [
                                confirm_input := dmc.PasswordInput(
                                    label="Confirm", size="md", required=True
                                ),
                                dmc.Flex(
                                    [
                                        create_button := dmc.Button("Create"),
                                        dmc.Space(w=10),
                                        back_button := dmc.Button("Back"),
                                    ]
                                ),
                            ],
                            w="100%",
                        ),
                        keepMounted=True,
                    ),
                ],
                flex="column",
            ),
        )
    )
)
"""Layout for login page. Embedded into `livetrivia._app` at `dash.page_container`."""


@app.callback(
    dash.Output(token_store, "data", allow_duplicate=True),
    dash.Output(user_store, "data", allow_duplicate=True),
    dash.Input(login_button, "n_clicks"),
    dash.State(email_input, "value"),
    dash.State(password_input, "value"),
    prevent_initial_call=True,
)
async def on_login(_: int, email: str | None, password: str | None):
    """Callback triggered when the user clicks login. Performs an API call on behalf of the user."""
    if not email or not password:
        raise de.PreventUpdate()
    user: LoginRequest = LoginRequest(email=email, password=password)
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.post("api/sessions/login", json=user.model_dump()) as session_response,
    ):
        if session_response.status >= 400:
            raise de.PreventUpdate()
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
    """Callback triggered when the user clicks sign up. Performs an API call."""
    if not email or not password:
        raise de.PreventUpdate()
    user: LoginRequest = LoginRequest(email=email, password=password)
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        async with session.post(
            "api/users", json=user.model_dump()
        ) as session_response:
            if session_response.status >= 400:
                raise de.PreventUpdate()
        async with session.post(
            "api/sessions/login", json=user.model_dump()
        ) as login_response:
            if login_response.status >= 400:
                raise de.PreventUpdate()
            token = await login_response.json()
    return token, email


update_current_menu: ClientsideFunctionType = app.clientside_callback(
    dash.ClientsideFunction("login", "updateCurrentMenu"),
    dash.Output(login_collapse, "opened"),
    dash.Output(create_collapse, "opened"),
    dash.Input(new_button, "n_clicks"),
    dash.Input(back_button, "n_clicks"),
    prevent_initial_call=True,
)
"""Callback to toggle between the login and create account screens."""


redirect_to_account: ClientsideFunctionType = app.clientside_callback(
    dash.ClientsideFunction("login", "redirectToAccount"),
    dash.Input(create_button, "n_clicks"),
    dash.Input(login_button, "n_clicks"),
    dash.Input(token_store, "data"),
    dash.Input(user_store, "data"),
)
"""Callback to redirect the router to refresh. This triggers the callback `on_navigate` in `livetrivia._app` (i.e. navigate to `/accounts` after sign-[up|in])."""


update_state_login: ClientsideFunctionType = app.clientside_callback(
    dash.ClientsideFunction("login", "updateStateLogin"),
    dash.Output(login_button, "disabled"),
    dash.Input(email_input, "value"),
    dash.Input(password_input, "value"),
    prevent_initial_call=True,
)
"""Callback to update the disabled/enabled state of the login button."""


update_state_create: ClientsideFunctionType = app.clientside_callback(
    dash.ClientsideFunction("login", "updateStateCreate"),
    dash.Output(create_button, "disabled"),
    dash.Input(email_input, "value"),
    dash.Input(password_input, "value"),
    dash.Input(confirm_input, "value"),
    prevent_initial_call=True,
)
"""Callback to update the disabled/enabled state of the create account button."""


dash.register_page(
    getmod(__name__),
    path="/login",
    layout=layout,
)
