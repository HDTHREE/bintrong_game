from dash import register_page, dcc
import dash_mantine_components as dmc
from livetrivia.utils import getmod


email_input = dmc.TextInput(
    placeholder="user@example.com",
    label="Email",
    size="md",
    required=True,
)

password_input = dmc.PasswordInput(label="Password", size="md", required=True)


confirm_input = dmc.PasswordInput(label="Confirm", size="md", required=True)


login_button = dmc.Button("Login")


new_button = dmc.Button("New?")


create_button = dmc.Button("Create")


back_button = dmc.Button("Back")




login_collapse = dmc.Collapse(
    children=dmc.Flex([login_button, dmc.Space(w=10), new_button]),
    keepMounted=True,
    opened=True,
)


create_collapse = dmc.Collapse(
    children=dmc.Stack(
        [confirm_input, dmc.Flex([create_button, dmc.Space(w=10), back_button])],
        w="100%",
    ),
    keepMounted=True,
)


login = dmc.Center(
    dmc.Card(
        w="60vw",
        children=dmc.Fieldset(
            children=[
                email_input,
                dmc.Space(h=10),
                password_input,
                dmc.Space(h=10),
                login_collapse,
                create_collapse,
            ],
            flex="column",
        ),
    )
)


layout: dmc.AppShellMain = dmc.AppShellMain(children=login)


register_page(
    getmod(__name__),
    path="/login",
    layout=layout,
)
