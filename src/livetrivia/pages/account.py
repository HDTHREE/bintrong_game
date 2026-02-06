import dash
import dash.exceptions as de
import aiohttp
import dash_mantine_components as dmc
from livetrivia.utils import getenvs, getmod
from livetrivia.shared_components import user_store, token_store


app: dash.Dash = dash.get_app()
"""Reference to global dash object."""


BACKEND_URL: str = getenvs(logger=app.logger)
"""URL to backend service."""


layout: dmc.AppShellMain = dmc.AppShellMain(
    children=dmc.Center(
        children=dmc.Card(
            children=dmc.Fieldset(
                children=dmc.Stack(
                    [
                        display_email := dmc.TextInput(
                            label="Email",
                            disabled=True,
                        ),
                        sign_out_button := dmc.Button("Sign out"),
                        sign_out_devices_button := dmc.Button(
                            children="Clear Existing Sessions",
                            disabled=True,  # TODO NYI
                        ),
                    ]
                )
            ),
            w="60vw",
            h="100%",
            mah="40vh",
        ),
        h="100vh",
    )
)
"""Layout for account page. Embedded into `livetrivia._app` at `dash.page_container`."""


@app.callback(
    dash.Input(sign_out_button, "n_clicks"),
    dash.State(token_store, "data"),
    running=[
        (dash.Output(user_store, "data", allow_duplicate=True), None, None),
        (dash.Output(token_store, "data", allow_duplicate=True), None, None),
    ],
    prevent_initial_call=True,
)
async def on_signout(n_clicks: int | None, token: dict):
    """Callback that fires when the user clicks log out. Logs out session and deletes it."""
    # This will fire on page load (regardless of the value of prevent_initial_call) so check if `None` for first trigger.
    if n_clicks is None or not token or not token.get("access_token"):
        raise de.PreventUpdate()
    params: dict = {"access_token": token["access_token"]}
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.post(url="api/sessions/logout", params=params) as logout_response,
    ):
        async with session.delete(
            url="api/sessions/", params=params
        ) as delete_session_response:
            await logout_response.json()
            await delete_session_response.json()


app.clientside_callback(
    dash.ClientsideFunction("accounts", "updateDisplay"),
    dash.Output(display_email, "value"),
    dash.Input(user_store, "data"),
)
"""Callback to control the text field displaying the users email."""


app.clientside_callback(
    dash.ClientsideFunction("accounts", "updateStateSignout"),
    dash.Output(sign_out_button, "disabled"),
    dash.Input(user_store, "data"),
)
"""Callback to update the disabled/enabled state of the sign off account button."""


app.clientside_callback(
    dash.ClientsideFunction("accounts", "redirectToLogin"),
    dash.Input(sign_out_button, "n_clicks"),
    dash.Input(sign_out_devices_button, "n_clicks"),
)
"""Callback to redirect the router away to the login screen."""


dash.register_page(
    getmod(__name__),
    path="/account",
    layout=layout,
)
