import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod

dash.register_page(
    getmod(__name__),
    path="/",
    layout=dmc.AppShellMain(children=dmc.Card()),
)
