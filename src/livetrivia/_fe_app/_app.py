#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.dash.env")
finally:
    ...
from dash import (
    html,
    dcc,
    page_container,
    page_registry,
    Dash,
    ClientsideFunction,
    _dash_renderer as dash_renderer,
)
import dash
import dash_mantine_components as dmc
from livetrivia.utils import assets_folder, pages_folder
from livetrivia._fe_app.components import token_store, user_store


dash_renderer._set_react_version("18.2.0")


app: Dash = Dash(
    use_pages=True,
    pages_folder=pages_folder,
    assets_folder=assets_folder,
    prevent_initial_callbacks="initial_duplicate",
    external_scripts=["https://unpkg.com/dash.nprogress@latest/dist/dash.nprogress.js"],
)


links = [html.Div(dcc.Link(p["name"], href=p["path"])) for p in page_registry.values()]


avatar = dmc.Avatar()


app.layout = dmc.MantineProvider(
    children=dmc.AppShell(
        header={"height": "8vh"},
        children=[
            dmc.AppShellHeader(children=links + [avatar]),
            page_container,
            token_store,
            user_store,
        ],
    )
)

app.clientside_callback(
    ClientsideFunction("layout", "setInitials"),
    dash.Output(avatar, "children"),
    dash.Input(user_store, "data"),
)

if __name__ == "__main__":
    app.run(port=7777, debug=False)
