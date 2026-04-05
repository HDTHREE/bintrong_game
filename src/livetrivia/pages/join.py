"""Module that contains code pertaining to the join page."""
import dash
import aiohttp
import dash_mantine_components as dmc
from livetrivia.utils import getmod, getenvs, ClientsideFunctionType
from livetrivia.shared_components import token_store, user_store


app: dash.Dash = dash.get_app()

BACKEND_URL: str = getenvs(logger=app.logger)


layout: dmc.AppShellMain = dmc.AppShellMain(
    style={"overflow": "hidden", "height": "100%"},
    children=dmc.Center(
        children=dmc.Card(
            children=[
                dmc.Fieldset(
                    children=dmc.Stack(
                        [
                            dmc.Title("Join", order=2),
                            game_code_input := dmc.PinInput(
                                placeholder="0",
                                size="md",
                                w="100%",
                                length=6,
                                styles={
                                    "root": {"width": "100%"},
                                    "pinInput": {"flex": 1},
                                    "input": {"width": "100%"},
                                },
                                type="alphanumeric",
                                oneTimeCode=False,
                            ),
                            join_button := dmc.Button("Play!"),
                        ]
                    )
                ),
                dmc.Space(h=5),
                dmc.Fieldset(
                    children=[
                        dmc.Space(h=2),
                        dmc.Group(
                            grow=True,
                            preventGrowOverflow=True,
                            align="flex-end",
                            children=[
                                questions_select := dmc.Select(maw="100%", label="Questions"),
                                host_button := dmc.Button(children="Host", maw="20%"),
                            ]
                        )
                    ]
                )
            ],
            w="60vw",
            h="100%",
            mah="40vh",
        ),
        h="calc(100vh - 8vh)",
    )
)
"""Layout for join page. Embedded into `livetrivia._app` at `dash.page_container`."""


update_state_code: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("join", "updateStateCode"),
    dash.Output(join_button, "disabled"),
    dash.Input(game_code_input, "value"),
)
"""Callback to update the disabled/enabled state of the join button."""


update_state_host_button: ClientsideFunctionType = dash.clientside_callback(
    dash.ClientsideFunction("join", "updateStateHostButton"),
    dash.Output(host_button, "disabled"),
    dash.Input(questions_select, "value"),
)
"""Callback to update the disabled/enabled state of the host button."""


@app.callback(
    dash.Output(questions_select, "data"),
    dash.Input(user_store, "data"),
    dash.State(token_store, "data"),
)
async def populate_questions_select(_: dict, token: dict):
    """Callback triggered when user data changes. Fetches available anki files for the user."""
    if not token or not token.get("access_token"):
        return []
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    async with aiohttp.ClientSession(BACKEND_URL) as session:
        async with session.get("api/files/anki/", headers=headers) as resp:
            if resp.status != 200:
                return []
            files: list[dict] = await resp.json()
    return [{"value": str(f["id"]), "label": f["prefix"].split("/")[-1]} for f in files]


dash.register_page(
    getmod(__name__),
    path="/join",
    layout=layout,
)
