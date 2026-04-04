import dash
import base64
import dash_iconify as di
import dash.exceptions as de
import dash_mantine_components as dmc
import dash_ag_grid as dag
import aiohttp
from livetrivia.utils import getmod, getenvs, ClientsideFunctionType
from livetrivia.shared_components import token_store, user_store


app: dash.Dash = dash.get_app()
"""Reference to global dash object."""


BACKEND_URL: str = getenvs(logger=app.logger)
"""URL to backend service."""


EXTS = (
    ".akpg",
    ".docx",
    ".pdf",
    ".txt",
)  # TODO This should prob be not based on extension and based on media groups
"""Accepted file extensions for upload."""


layout: dmc.AppShellMain = dmc.AppShellMain(
    children=dmc.Center(
        children=dmc.Card(
            children=dmc.Stack(
                children=[
                    dmc.Title("Your Files", order=2),
                    dmc.Flex(
                        w="100%",
                        justify="space-around",
                        children=[
                            upload_button := dmc.Button(
                                upload := dash.dcc.Upload(
                                    children=dmc.Text(children="Upload File"),
                                    multiple=False,
                                    accept=",".join(EXTS),
                                ),
                                w="48%",
                                leftSection=di.DashIconify(icon="ic:round-file-upload"),
                            ),
                            yt_button := dmc.Button(
                                children="YouTube",
                                color="red",
                                w="48%",
                                leftSection=di.DashIconify(
                                    icon="ic:outline-ondemand-video"
                                ),
                            ),
                        ],
                    ),
                    grid := dag.AgGrid(
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
                                    "rightIcon": "ic:round-delete",
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
                                    "rightIcon": "ic:round-file-download",
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
                    ),
                    download := dash.dcc.Download(),
                    modal := dmc.Modal(
                        modal_fieldset := dmc.Fieldset(), keepMounted=True
                    ),
                ]
            ),
            w="100vw",
            h="100vh",
            style={"overflow": "hidden", "boxSizing": "border-box"},
        ),
        h="100vh",
        style={"overflow": "hidden", "boxSizing": "border-box"},
    ),
)
"""Layout for files page. Embedded into `livetrivia._app` at `dash.page_container`."""


@app.callback(
    dash.Output(grid, "rowData", allow_duplicate=True),
    dash.Input(user_store, "data"),
    dash.State(token_store, "data"),
)
async def update_files_grid(_: dict, token: dict):
    """Callback triggered when user data changes. Fetches all files for the user."""
    if not token or not token.get("access_token"):
        return []
    access_token = token["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    async with (
        aiohttp.ClientSession(BACKEND_URL) as session,
        session.get("api/files/data/", headers=headers) as resp,
    ):
        if resp.status != 200:
            return []
        return await resp.json()


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
    render_data: dict, row_data: list[dict], _: str, token: dict
):
    """Callback triggered when user clicks a grid action button (delete/download)."""
    if not render_data or not token or not token.get("access_token"):
        raise de.PreventUpdate()
    try:
        row_id: int = int(render_data.get("rowId"))
        action: str = str(render_data.get("colId"))

        access_token: str = str(token["access_token"])

        row: dict = row_data[row_id]
        file_id: str = str(row.get("id"))
    except KeyError as e:
        raise de.PreventUpdate() from e

    headers: dict = {"Authorization": f"Bearer {access_token}"}
    download_data: dash.NoUpdate | dict = dash.no_update
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        if action.lower() == "delete":
            async with session.delete(f"api/files/{file_id}", headers=headers) as resp:
                if resp.status != 204:
                    raise de.PreventUpdate()
        elif action.lower() == "download":
            async with session.get(f"api/files/{file_id}", headers=headers) as resp:
                if resp.status != 200:
                    raise de.PreventUpdate()
                content: bytes = await resp.read()
                filename: str | None = None
                cd: str | None = resp.headers.get("Content-Disposition")
                if cd and "filename=" in cd:
                    filename = cd.split("filename=")[-1].strip('"')
                else:
                    filename = row.get("prefix", "downloaded_file")
                    if "/" in filename:
                        filename = filename.split("/")[-1]
                download_data = dash.dcc.send_bytes(content, filename=filename)
        else:
            raise de.PreventUpdate()
        async with session.get("api/files/data/", headers=headers) as resp:
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
async def upload_file(contents: str, filename: str, token: dict):
    """Callback triggered when user uploads a file. Sends file to backend API."""
    if not contents or not filename or not token or not token.get("access_token"):
        raise de.PreventUpdate()
    _, b64data = contents.split(",", 1)
    file_bytes: bytes = base64.b64decode(b64data)
    access_token: str = token["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        data: aiohttp.FormData = aiohttp.FormData(
            fields={
                "name": "file",
                "value": file_bytes,
                "filename": filename,
                "content_type": "application/octet-stream",
            }
        )
        async with session.post("api/files/", data=data, headers=headers) as resp:
            if resp.status != 201:
                raise de.PreventUpdate()
        async with session.get("api/files/data/", headers=headers) as resp:
            if resp.status != 200:
                raise de.PreventUpdate()
            return await resp.json()


open_upload: ClientsideFunctionType = app.clientside_callback(
    dash.ClientsideFunction("files", "openUpload"),
    dash.Input(upload_button, "n_clicks"),
    prevent_initial_call=True,
)
"""Callback that opens the upload component. Part of the button isn't in the upload."""


dash.register_page(
    getmod(__name__),
    path="/files",
    layout=layout,
)
