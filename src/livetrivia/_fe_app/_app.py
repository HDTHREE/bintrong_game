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
from livetrivia._fe_app.components import token_store, user_store, interval, url


dash._dash_renderer._set_react_version("18.2.0")


app: dash.Dash = dash.Dash(
    use_pages=True,
    pages_folder=pages_folder,
    assets_folder=assets_folder,
    prevent_initial_callbacks="initial_duplicate",
    external_scripts=["https://unpkg.com/dash.nprogress@latest/dist/dash.nprogress.js"],
)

BACKEND_URL: str = getenvs()


home_page = dash.page_registry["home"]


join_page = dash.page_registry["join"]


account_page = dash.page_registry["account"]


login_page = dash.page_registry["login"]


files_page = dash.page_registry["files"]


home_link = dmc.NavLink(
    label=dmc.Text(home_page["name"], w=170),
    href=home_page["path"],
    leftSection=di.DashIconify(icon="ic:round-home"),
)


join_link = dmc.NavLink(
    label=dmc.Text(join_page["name"], w=170),
    href=join_page["path"],
    leftSection=di.DashIconify(icon="ic:round-connect-without-contact"),
)


login_link = dmc.NavLink(
    label=dmc.Text(login_page["name"], w=170),
    href=login_page["path"],
    leftSection=di.DashIconify(icon="ic:round-login"),
)


files_link = dmc.NavLink(
    label=dmc.Text(files_page["name"], w=170),
    href=files_page["path"],
    leftSection=di.DashIconify(icon="ic:round-drive-file-move"),
)


avatar = dmc.Avatar()


avatar_link = dmc.NavLink(
    label=dmc.Text(account_page["name"], w=170),
    leftSection=avatar,
    href=account_page["path"],
)


header_children = [home_link, join_link, files_link, login_link, avatar_link]


app.layout = dmc.MantineProvider(
    children=dmc.AppShell(
        header={"height": "8vh"},
        children=[
            dmc.AppShellHeader(
                children=dmc.Flex(
                    p=3, w="100%", h="100%", children=header_children, justify="right"
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


app.clientside_callback(
    dash.ClientsideFunction("layout", "setStyle"),
    dash.Output(login_link, "style"),
    dash.Output(avatar_link, "style"),
    dash.Input(user_store, "data"),
)


@app.callback(
    dash.Output(url, "pathname"),
    dash.Input(url, "pathname"),
    dash.State(token_store, "data"),
    dash.State(user_store, "data"),
    prevent_initial_call=True,
)
def on_navigate(url: str | None, token: dict | None, user: str | None):
    session: bool = token and user
    real = {"/files", "/account", "/", "/login", "/join"}
    protected = {"/files", "/account"}

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
    dash.Input(url, "pathname"),
    dash.Input(token_store, "data"),
    dash.State(user_store, "id"),
    dash.Input(interval, "n_intervals"),
    dash.State(interval, "id"),
)
async def on_refresh(_: str | None, token: dict, email: str | None, __: int, id: str):
    if dash.ctx.triggered_id != id and token:
        raise de.PreventUpdate()
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        # Get a guest session if no email.
        if not email or not token:
            async with session.post("api/sessions/guest") as session_response:
                return await session_response.json(), dash.no_update
        # Otherwise, use refresh the session.
        try:
            params = {"refresh_token": token["refresh_token"]}
            async with session.post(
                "api/sessions/refresh", params=params
            ) as session_response:
                return await session_response.json(), dash.no_update
        except:
            return None, None


if __name__ == "__main__":
    app.run(port=7777, debug=False)
