import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod


layout: dmc.AppShellMain = dmc.AppShellMain(children=dmc.Card())
"""Layout for home page. Embedded into `livetrivia._app` at `dash.page_container`."""


dash.register_page(
    getmod(__name__),
    path="/",
    layout=layout,
)
