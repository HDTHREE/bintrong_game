import asyncio
import dash
import uuid
import dash.exceptions as de
import aiohttp
import dash
import dash_mantine_components as dmc
from livetrivia.utils import getenvs, getmod
from livetrivia._fe_app.components import user_store, token_store

display_email = dmc.TextInput(
    label="Email",
    disabled=True,
)


sign_out_button = dmc.Button("Sign out")


sign_out_devices_button = dmc.Button("Clear Existing Sessions" ,disabled=True) # TODO NYI


account_card = dmc.Card(
    dmc.Fieldset(dmc.Stack([display_email, sign_out_button, sign_out_devices_button])),
    w="60vw",
    h="100%",
    mah="40vh",
)


file_card = dmc.Card(mah="40vh")


layout = dmc.Center(dmc.Stack(children=[account_card, file_card]), h="100vh")


dash.register_page(
    getmod(__name__),
    path="/account",
    layout=layout,
)

app: dash.Dash = dash.get_app()


BACKEND_URL: str = getenvs()


app.clientside_callback(
    dash.ClientsideFunction("accounts", "setDisplay"),
    dash.Output(display_email, "value"),
    dash.Input(user_store, "data"),
)


@app.callback(
    dash.Output(user_store, "data", allow_duplicate=True),
    dash.Output(token_store, "data"),
    dash.Input(sign_out_button, "n_clicks"),
    dash.State(token_store, "data"),
)
async def on_signout(n_clicks: int | None, token: dict):
    if not token or not n_clicks:
        raise de.PreventUpdate()
    params = {"access_token": token["access_token"]}
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.post(url="api/sessions/logout", params=params) as logout_response,
    ):
        async with session.delete(url="api/sessions/", params=params) as delete_session_response:
            *_, = await asyncio.gather(logout_response.json(), delete_session_response.json())
    return None, None
