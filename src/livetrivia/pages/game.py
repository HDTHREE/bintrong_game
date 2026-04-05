"""Module that contains code pertaining to the game page."""
import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod, ClientsideFunctionType
from livetrivia.shared_components import url


app: dash.Dash = dash.get_app()

layout: dmc.AppShellMain = dmc.AppShellMain(
    px=0,
    pb=0,
    style={"overflow": "hidden"},
    children=dash.html.Embed(
        id="game-embed",
        src="",
        style={"width": "100%", "height": "calc(100vh - 8vh)", "border": "none", "display": "block"},
    ),
)
"""Layout for game page. Embedded into `livetrivia._app` at `dash.page_container`."""


set_game_src: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("game", "setGameSrc"),
    dash.Output("game-embed", "src"),
    dash.Input(url, "pathname"),
)
"""Callback to set the embed src from the current pathname."""


dash.register_page(
    getmod(__name__),
    path_template="/game/<game_code>",
    layout=layout,
)
