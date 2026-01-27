from dash import register_page
import dash_mantine_components as dmc
from livetrivia.utils import getmod


files_center = dmc.Center(dmc.Card(
    
), w="80vw", h="100%")


layout = dmc.AppShellMain(children=files_center)


register_page(
    getmod(__name__),
    path="/files",
    layout=layout,
)
