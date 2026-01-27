from dash import register_page
import dash_mantine_components as dmc
from livetrivia.utils import getmod

register_page(
    getmod(__name__),
    path="/files",
    layout=dmc.AppShellMain(children=dmc.Card()),
)
