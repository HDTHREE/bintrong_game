from dash import register_page
import dash_mantine_components as dmc
from livetrivia.utils import getmod

display_email = dmc.TextInput(
    label="Email",
    disabled=True
)


sign_out_button = dmc.Button("Sign out")


sign_out_devices_button = dmc.Button("Clear Existing Sessions")


account_card = dmc.Card(dmc.Fieldset(dmc.Stack([display_email, sign_out_button, sign_out_devices_button])), w="60vw", h="100%", mah="40vh")


file_card = dmc.Card(mah="40vh")


layout = dmc.Center(dmc.Stack(children=[account_card, file_card]), h="100vh")


register_page(
    getmod(__name__),
    path="/account",
    layout=layout,
)
