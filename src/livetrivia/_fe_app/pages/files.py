
import dash
import dash_mantine_components as dmc
import dash_ag_grid as dag
import pandas as pd
import aiohttp
from livetrivia.utils import getmod, getenvs
from livetrivia._fe_app.components import token_store, user_store

register_page = dash.register_page

app: dash.Dash = dash.get_app()

BACKEND_URL = getenvs()


grid = dag.AgGrid(
    id="files-grid",
    columnDefs=[
        {
            "headerName": "File Name",
            "field": "prefix",
            "flex": 1,
            "valueGetter": { "function": "nameGetter(params)" },
        },
        {"headerName": "File ID", "field": "id", "flex": 1},
    ],
    className="ag-theme-alpine",
    dashGridOptions={"pagination": True, "paginationPageSize": 10},
)

files_center = dmc.Center(
    dmc.Card(
        dmc.Stack([
            dmc.Title("Your Files", order=2),
            grid,
        ]),
        w="80vw",
        h="100%",
    ),
    h="100vh",
)

layout = dmc.AppShellMain(children=files_center)

register_page(
    getmod(__name__),
    path="/files",
    layout=layout,
)

@app.callback(
    dash.Output(grid, "rowData"),
    dash.Input(user_store, "data"),
    dash.State(token_store, "data"),
)
async def update_files_grid(_: dict, token):
    if not token or not token.get("access_token"):
        return []
    access_token = token["access_token"]
    params = {"access_token": access_token}
    async with aiohttp.ClientSession(BACKEND_URL) as session, session.get("api/files/data/", params=params) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()
        return data
