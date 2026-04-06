"""Module that contains code pertaining to the join page."""

import dash
import dash.exceptions as de
import aiohttp
import dash_mantine_components as dmc
from livetrivia.utils import getmod, getenvs, ClientsideFunctionType
from livetrivia.shared_components import token_store, user_store, url


app: dash.Dash = dash.get_app()

BACKEND_URL: str = getenvs(logger=app.logger)


layout: dmc.AppShellMain = dmc.AppShellMain(
    style={"overflow": "hidden", "height": "100%"},
    children=dmc.Center(
        children=dmc.Card(
            children=[
                dmc.Fieldset(
                    children=dmc.Stack(
                        [
                            dmc.Title("Join", order=2),
                            game_code_input := dmc.PinInput(
                                placeholder="0",
                                size="md",
                                w="100%",
                                length=6,
                                styles={
                                    "root": {"width": "100%"},
                                    "pinInput": {"flex": 1},
                                    "input": {"width": "100%"},
                                },
                                type="alphanumeric",
                                oneTimeCode=False,
                            ),
                            join_button := dmc.Button("Play!"),
                        ]
                    )
                ),
                dmc.Space(h=5),
                dmc.Fieldset(
                    children=[
                        dmc.Space(h=2),
                        dmc.Group(
                            grow=True,
                            preventGrowOverflow=True,
                            align="flex-end",
                            children=[
                                questions_select := dmc.Select(
                                    maw="100%",
                                    label="Host",
                                    placeholder="questions.apkg",
                                ),
                                host_button := dmc.Button(children="Host", maw="20%"),
                            ],
                        ),
                    ]
                ),
                dmc.Space(h=5),
                join_alert := dmc.Alert(
                    id="join-alert",
                    color="red",
                    style={"display": "none"},
                    children="",
                ),
            ],
            w="60vw",
            h="100%",
            mah="40vh",
        ),
        h="calc(100vh - 8vh)",
    ),
)
"""Layout for join page. Embedded into `livetrivia._app` at `dash.page_container`."""


update_state_code: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("join", "updateStateCode"),
    dash.Output(join_button, "disabled"),
    dash.Input(game_code_input, "value"),
)
"""Callback to update the disabled/enabled state of the join button."""


update_state_host_button: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("join", "updateStateHostButton"),
    dash.Output(host_button, "disabled"),
    dash.Input(questions_select, "value"),
)
"""Callback to update the disabled/enabled state of the host button."""


@app.callback(
    dash.Output(questions_select, "data"),
    dash.Input(user_store, "data"),
    dash.State(token_store, "data"),
)
async def populate_questions_select(_: dict, token: dict):
    """Callback triggered when user data changes. Fetches available anki files for the user."""
    if not token or not token.get("access_token"):
        return []
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        async with session.get("api/files/anki/", headers=headers) as resp:
            if resp.status != 200:
                return []
            files: list[dict] = await resp.json()
    return [{"value": str(f["id"]), "label": f["prefix"].split("/")[-1]} for f in files]


@app.callback(
    dash.Output(url, "pathname", allow_duplicate=True),
    dash.Output(join_alert, "children", allow_duplicate=True),
    dash.Output(join_alert, "style", allow_duplicate=True),
    dash.Output("game-player", "data", allow_duplicate=True),
    dash.Input(join_button, "n_clicks"),
    dash.State(game_code_input, "value"),
    dash.State(token_store, "data"),
    prevent_initial_call=True,
)
async def on_join(n_clicks: int | None, game_code: str | None, token: dict | None):
    """Callback triggered when the join button is clicked. Joins the game and redirects."""
    if not n_clicks:
        raise de.PreventUpdate()
    if not token or not token.get("access_token"):
        return (
            dash.no_update,
            "You must have a session to join a game.",
            {"display": "block"},
            dash.no_update,
        )
    game_code = game_code.upper()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        async with session.post(
            "api/games/join", params={"game_code": game_code}, headers=headers
        ) as resp:
            if resp.status == 201:
                game_player = await resp.json()
                return (
                    f"/game/{game_code}",
                    dash.no_update,
                    dash.no_update,
                    {"id": game_player["id"]},
                )
            data = await resp.json()
            detail = data.get("detail", "Failed to join game.")
    return dash.no_update, detail, {"display": "block"}, dash.no_update


@app.callback(
    dash.Output(url, "pathname", allow_duplicate=True),
    dash.Output(join_alert, "children", allow_duplicate=True),
    dash.Output(join_alert, "style", allow_duplicate=True),
    dash.Output("game-player", "data", allow_duplicate=True),
    dash.Input(host_button, "n_clicks"),
    dash.State(questions_select, "value"),
    dash.State(token_store, "data"),
    prevent_initial_call=True,
)
async def on_host(n_clicks: int | None, file_id: str | None, token: dict | None):
    """Callback triggered when the host button is clicked. Creates and starts a game, then redirects."""
    if not n_clicks:
        raise de.PreventUpdate()
    if not token or not token.get("access_token"):
        return (
            dash.no_update,
            "You must have a session to host a game.",
            {"display": "block"},
            dash.no_update,
        )
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        async with session.post("api/games/", headers=headers) as resp:
            if resp.status != 201:
                data = await resp.json()
                return (
                    dash.no_update,
                    data.get("detail", "Failed to create game."),
                    {"display": "block"},
                    dash.no_update,
                )
            game = await resp.json()
        game_id = game["id"]
        game_code = game["game_code"]
        async with session.post(
            f"api/games/{game_id}/file", params={"file_id": file_id}, headers=headers
        ) as resp:
            if resp.status != 200:
                data = await resp.json()
                await session.post(
                    f"api/games/{game_id}/end", json={"force": True}, headers=headers
                )
                return (
                    dash.no_update,
                    data.get("detail", "Failed to set game file."),
                    {"display": "block"},
                    dash.no_update,
                )
        async with session.post(f"api/games/{game_id}/start", headers=headers) as resp:
            if resp.status != 200:
                data = await resp.json()
                await session.post(
                    f"api/games/{game_id}/end", json={"force": True}, headers=headers
                )
                return (
                    dash.no_update,
                    data.get("detail", "Failed to start game."),
                    {"display": "block"},
                    dash.no_update,
                )
        async with session.post(
            "api/games/join", params={"game_code": game_code}, headers=headers
        ) as resp:
            game_player_data = (
                {"id": (await resp.json()).get("id")}
                if resp.status in (200, 201)
                else dash.no_update
            )
    return f"/game/{game_code}", dash.no_update, dash.no_update, game_player_data


dash.register_page(
    getmod(__name__),
    path="/join",
    layout=layout,
)
