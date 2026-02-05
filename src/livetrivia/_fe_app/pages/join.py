import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod


game_code_input = dmc.PinInput(
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
)


join_button = dmc.Button("Play!")


join_card = dmc.Card(
    dmc.Fieldset(
        dmc.Stack(
            [
                dmc.Title("Join", order=2),
                game_code_input,
                join_button,
            ]
        )
    ),
    w="60vw",
    h="100%",
    mah="40vh",
)


join_center = dmc.Center(join_card, h="100vh")


layout = dmc.AppShellMain(children=join_center)


dash.clientside_callback(
    dash.ClientsideFunction("join", "updateState"),
    dash.Output(join_button, "disabled"),
    dash.Input(game_code_input, "value"),
)


dash.register_page(
    getmod(__name__),
    path="/join",
    layout=layout,
)
