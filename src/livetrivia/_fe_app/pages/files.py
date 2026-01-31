import dash
import typing_extensions as tp
import dash.exceptions as de
import dash_mantine_components as dmc
import dash_ag_grid as dag
import aiohttp
from dash import ctx
from livetrivia.utils import getmod, getenvs
from livetrivia._fe_app.components import token_store, user_store

register_page = dash.register_page

app: dash.Dash = dash.get_app()

BACKEND_URL = getenvs()


grid = dag.AgGrid(
    columnDefs=[
        {
            "headerName": "File Name",
            "field": "prefix",
            "flex": 3,
            "valueGetter": {"function": "nameGetter(params)"},
        },
        {"headerName": "File ID", "field": "id", "flex": 3},
        {
            "headerName": "Delete",
            "cellRenderer": "dmcButton",
            "cellRendererParams": {
                "rightIcon": "ph:trash",
                "value": "Delete",
                "color": "red",
            },
            "field": "user_id",
            "colId": "Delete",
            "flex": 1,
        },
        {
            "headerName": "Download",
            "cellRenderer": "dmcButton",
            "cellRendererParams": {
                "rightIcon": "ph:download",
                "value": "Download",
            },
            "field": "user_id",
            "colId": "Download",
            "flex": 1,
        },
    ],
    className="ag-theme-alpine",
    dashGridOptions={
        "pagination": True,
        "paginationPageSize": 10,
        "paginationPageSizeOptions": [10, 25, 50, 100],
        "paginationMaxPageSize": 100,
    },
)

download = dash.dcc.Download()


files_center = dmc.Center(
    dmc.Card(
        dmc.Stack(
            [
                dmc.Title("Your Files", order=2),
                grid,
                download,
            ]
        ),
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
    dash.Output(grid, "rowData", allow_duplicate=True),
    dash.Input(user_store, "data"),
    dash.State(token_store, "data"),
)
async def update_files_grid(_: dict, token):
    if not token or not token.get("access_token"):
        return []
    access_token = token["access_token"]
    params = {"access_token": access_token}
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.get("api/files/data/", params=params) as resp,
    ):
        if resp.status != 200:
            return []
        data = await resp.json()
        return data



@app.callback(
    dash.Output(grid, "rowData", allow_duplicate=True),
    dash.Output(download, "data"),
    dash.Input(grid, "cellRendererData"),
    dash.State(grid, "rowData"),
    dash.State(user_store, "data"),
    dash.State(token_store, "data"),
    prevent_initial_call=True,
)
async def handle_file_action(render_data: dict, row_data: list[dict], user: str, token: dict):
    if not render_data or not token or not token.get("access_token"):
        raise de.PreventUpdate()
    row_id: int = int(render_data.get("rowId")) # TODO this might need to be rowIndex
    action: str = str(render_data.get("colId"))

    access_token: str = str(token["access_token"])

    row = row_data[row_id]
    file_id = row["id"]

    params: dict = {"access_token": access_token}
    download_data: dash.NoUpdate | dict = dash.no_update
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        if action.lower() == "delete":
            async with session.delete(f"api/files/{file_id}", params=params) as resp:
                if resp.status != 204:
                    raise de.PreventUpdate()
        elif action.lower() == "download":
            async with session.get(f"api/files/{file_id}", params=params) as resp:
                if resp.status != 200:
                    raise de.PreventUpdate()
                content = await resp.read()
                filename = None
                cd = resp.headers.get("Content-Disposition")
                if cd and "filename=" in cd:
                    filename = cd.split("filename=")[-1].strip('"')
                else:
                    filename = row.get("prefix", "downloaded_file")
                    if "/" in filename:
                        filename = filename.split("/")[-1]
                download_data = dash.dcc.send_bytes(content, filename=filename)
        async with session.get("api/files/data/", params=params) as resp:
            if resp.status != 200:
                raise de.PreventUpdate()
            data: dict = await resp.json()
            return data, download_data
