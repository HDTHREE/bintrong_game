import dash
import base64
import dash_iconify as di
import dash.exceptions as de
import dash_mantine_components as dmc
import dash_ag_grid as dag
import aiohttp
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


upload = dash.dcc.Upload(
    children=dmc.Button("Upload File", leftSection=di.DashIconify(icon="ph:upload")),
    multiple=False,
    style={"marginBottom": "1rem"},
)


files_center = dmc.Center(
    dmc.Card(
        dmc.Stack(
            [
                dmc.Title("Your Files", order=2),
                upload,
                grid,
                download,
            ]
        ),
        w="100vw",
        h="100vh",
        style={"overflow": "hidden", "boxSizing": "border-box"},
    ),
    h="100vh",
    style={"overflow": "hidden", "boxSizing": "border-box"},
)

layout = dmc.AppShellMain(
    children=files_center,
    style={
        "width": "100vw",
        "height": "100vh",
        "overflow": "hidden",
        "boxSizing": "border-box",
    },
)

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
async def handle_file_action(
    render_data: dict, row_data: list[dict], user: str, token: dict
):
    if not render_data or not token or not token.get("access_token"):
        raise de.PreventUpdate()
    row_id: int = int(render_data.get("rowId"))
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


@app.callback(
    dash.Output(grid, "rowData", allow_duplicate=True),
    dash.Input(upload, "contents"),
    dash.State(upload, "filename"),
    dash.State(token_store, "data"),
    prevent_initial_call=True,
)
async def upload_file(contents, filename, token: dict):
    if not contents or not filename or not token or not token.get("access_token"):
        raise de.PreventUpdate()
    header, b64data = contents.split(",", 1)
    file_bytes = base64.b64decode(b64data)
    access_token = token["access_token"]
    params = {"access_token": access_token}
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        form = aiohttp.FormData()
        form.add_field(
            "file",
            file_bytes,
            filename=filename,
            content_type="application/octet-stream",
        )
        async with session.post("api/files/", data=form, params=params) as resp:
            if resp.status != 201:
                raise de.PreventUpdate()
        async with session.get("api/files/data/", params=params) as resp:
            if resp.status != 200:
                raise de.PreventUpdate()
            return await resp.json()
