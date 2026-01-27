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
    _dash_renderer as dash_renderer,
)
import dash_mantine_components as dmc
from livetrivia.utils import load_callbacks, load_pages, assets_folder, pages_folder


dash_renderer._set_react_version("18.2.0")


app: Dash = Dash(
    use_pages=True,
    pages_folder=pages_folder,
    assets_folder=assets_folder,
    external_scripts=["https://unpkg.com/dash.nprogress@latest/dist/dash.nprogress.js"],
)


load_pages()
load_callbacks()


links = [html.Div(dcc.Link(p["name"], href=p["path"])) for p in page_registry.values()]


app.layout = dmc.MantineProvider(
    children=dmc.AppShell(
        header={"height": "8vh"},
        children=[
            dmc.AppShellHeader(children=links),
            page_container,
        ],
    )
)

if __name__ == "__main__":
    app.run(port=7777, debug=False)
