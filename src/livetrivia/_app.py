#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.dash.env")
finally:
    ...
import aiohttp
import dash_iconify as di
import dash
import dash.exceptions as de
import dash_mantine_components as dmc
from livetrivia.utils import assets_folder, getenvs, pages_folder
from livetrivia.shared_components import token_store, user_store, interval, url


dash._dash_renderer._set_react_version("18.2.0")


app: dash.Dash = dash.Dash(
    use_pages=True,
    pages_folder=pages_folder,
    assets_folder=assets_folder,
    prevent_initial_callbacks="initial_duplicate",
    external_scripts=["https://unpkg.com/dash.nprogress@latest/dist/dash.nprogress.js"],
)
"""Rerence from constructor call to global dash object."""


BACKEND_URL: str = getenvs(logger=app.logger)
"""URL to backend service."""


app.layout = dmc.MantineProvider(
    children=dmc.AppShell(
        header={"height": "8vh"},
        children=[
            dmc.AppShellHeader(
                children=dmc.Flex(
                    p=3,
                    w="100%",
                    h="100%",
                    children=[
                        home_link := dmc.NavLink(
                            label=dmc.Text(dash.page_registry["home"]["name"], w=170),
                            href=dash.page_registry["home"]["path"],
                            leftSection=di.DashIconify(icon="ic:round-home"),
                        ),
                        join_link := dmc.NavLink(
                            label=dmc.Text(dash.page_registry["join"]["name"], w=170),
                            href=dash.page_registry["join"]["path"],
                            leftSection=di.DashIconify(
                                icon="ic:round-connect-without-contact"
                            ),
                        ),
                        login_link := dmc.NavLink(
                            label=dmc.Text(dash.page_registry["login"]["name"], w=170),
                            href=dash.page_registry["login"]["path"],
                            leftSection=di.DashIconify(icon="ic:round-login"),
                        ),
                        files_link := dmc.NavLink(
                            label=dmc.Text(dash.page_registry["files"]["name"], w=170),
                            href=dash.page_registry["files"]["path"],
                            leftSection=di.DashIconify(icon="ic:round-drive-file-move"),
                        ),
                        avatar_link := dmc.NavLink(
                            label=dmc.Text(
                                dash.page_registry["account"]["name"], w=170
                            ),
                            leftSection=(avatar := dmc.Avatar()),
                            href=dash.page_registry["account"]["path"],
                        ),
                    ],
                    justify="right",
                )
            ),
            url,
            dash.page_container,
            token_store,
            user_store,
            interval,
        ],
    )
)


app.clientside_callback(
    dash.ClientsideFunction("layout", "setInitials"),
    dash.Output(avatar, "children"),
    dash.Input(user_store, "data"),
)
"""Callback that displays the first two characters of the email."""


app.clientside_callback(
    dash.ClientsideFunction("layout", "setStyle"),
    dash.Output(login_link, "style"),
    dash.Output(avatar_link, "style"),
    dash.Input(user_store, "data"),
)
"""Callback to toggle between displaying the login/account tab at the top."""


@app.callback(
    dash.Output(url, "pathname"),
    dash.Input(url, "pathname"),
    dash.State(token_store, "data"),
    dash.State(user_store, "data"),
    prevent_initial_call=True,
)
def on_navigate(url: str | None, token: dict | None, user: str | None):
    """Callback that triggers on navigation. Navigates users away from routes that require an account."""
    session: bool = token and user
    real: set = {"/files", "/account", "/", "/login", "/join"}
    protected: set = {"/files", "/account"}

    if not url or url not in real:
        return "/"
    if url in protected and not session:
        return "/login"
    if url == "/login" and session:
        return "/account"

    raise de.PreventUpdate()


@app.callback(
    dash.Output(token_store, "data", allow_duplicate=True),
    dash.Output(user_store, "data", allow_duplicate=True),
    dash.State(user_store, "id"),
    dash.State(interval, "id"),
    dash.Input(token_store, "data"),
    dash.Input(url, "pathname"),
    dash.Input(interval, "n_intervals"),
)
async def on_refresh(email: str | None, id: str, token: dict, *_: str | int | None):
    """Callback that triggers when a user refreshes or navigates to ensure a valid session."""
    if dash.ctx.triggered_id != id and token:
        raise de.PreventUpdate()
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        # Get a guest session if no email.
        if not email or not token:
            async with session.post("api/sessions/guest") as session_response:
                return await session_response.json(), dash.no_update
        # Otherwise, refresh the session.
        try:
            params = {"refresh_token": token["refresh_token"]}
            async with session.post(
                "api/sessions/refresh", params=params
            ) as session_response:
                return await session_response.json(), dash.no_update
        finally:
            return None, None


if __name__ == "__main__":
    app.run(port=7777, debug=True)
