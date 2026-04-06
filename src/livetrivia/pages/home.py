import dash
import dash_mantine_components as dmc
from livetrivia.utils import getmod


layout: dmc.AppShellMain = dmc.AppShellMain(
    children=dmc.Center(
        h="100%",
        children=dmc.Card(
            w="60vw",
            children=dmc.Stack(
                align="center",
                children=[
                    dmc.Image(src="/assets/logo.svg", w=120, h=120),
                    dmc.Text(
                        ta="center",
                        children=(
                            "Binturong is designed to be a FOSS game for students to "
                            "study questions using competition. A key goal is make "
                            "the solution freeware so anyone can host. The intent is "
                            "for the game application to provide options for "
                            "generating card packs via LLM. The distinguishing factor "
                            "of this project is to encourage competition in order to "
                            "trick users into studying. The application will be "
                            "designed to be short review games where players have a "
                            "score or survival objective. The player's goal will be "
                            "to control his or her character and select the correct "
                            "answer based on the game."
                        ),
                    ),
                ],
            ),
        ),
    )
)
"""Layout for home page. Embedded into `livetrivia._app` at `dash.page_container`."""


dash.register_page(
    getmod(__name__),
    path="/",
    layout=layout,
)
