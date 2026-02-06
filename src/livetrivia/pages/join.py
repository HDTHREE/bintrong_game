import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod


layout: dmc.AppShellMain = dmc.AppShellMain(
    children=dmc.Center(
        children=dmc.Card(
            children=dmc.Fieldset(
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
            w="60vw",
            h="100%",
            mah="40vh",
        ),
        h="100vh",
    )
)
"""Layout for join page. Embedded into `livetrivia._app` at `dash.page_container`."""


dash.clientside_callback(
    dash.ClientsideFunction("join", "updateState"),
    dash.Output(join_button, "disabled"),
    dash.Input(game_code_input, "value"),
)
"""Callback to update the disabled/enabled state of the join button."""


dash.register_page(
    getmod(__name__),
    path="/join",
    layout=layout,
)
