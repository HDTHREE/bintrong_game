"""Module that contains code pertaining to the game page."""

import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod, ClientsideFunctionType
from livetrivia.shared_components import url, game_player_store


app: dash.Dash = dash.get_app()

layout: dmc.AppShellMain = dmc.AppShellMain(
    px=0,
    pb=0,
    style={"overflow": "hidden"},
    children=[
        dash.html.Iframe(
            id="game-embed",
            src="",
            style={
                "width": "100%",
                "height": "calc(100vh - 8vh)",
                "border": "none",
                "display": "block",
                "visibility": "hidden",
            },
        ),
        dash.dcc.Interval(id="game-end-poll", interval=500),
    ],
)
"""Layout for game page. Embedded into `livetrivia._app` at `dash.page_container`."""


set_game_src: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("game", "setGameSrc"),
    dash.Output("game-embed", "src"),
    dash.Input(url, "pathname"),
    dash.State(game_player_store, "data"),
)
"""Callback to set the embed src from the current pathname."""

poll_game_ended: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("game", "pollGameEnded"),
    dash.Output(url, "pathname", allow_duplicate=True),
    dash.Input("game-end-poll", "n_intervals"),
    prevent_initial_call=True,
)
"""Callback to redirect to /join when the game server signals it has ended."""


dash.register_page(
    getmod(__name__),
    path_template="/game/<game_code>",
    layout=layout,
)
