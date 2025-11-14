import dash_extensions.enrich as dee
import dash_extensions.pages as dep
from dash import html, dcc, page_container, page_registry
import dash_mantine_components as dmc
from livetrivia.utils import load_pages


_app: dee.DashProxy = dee.DashProxy(
    use_pages=True, transforms=[dee.DataclassTransform(), dee.MultiplexerTransform()]
)


load_pages()


links = [html.Div(dcc.Link(p["name"], href=p["path"])) for p in page_registry.values()]


_app.layout = dmc.MantineProvider(
    children=dmc.AppShell(
        children=[
            dmc.AppShellHeader(children=links),
            page_container,
            dep.setup_page_components(),
        ]
    )
)


dep.set_page_container_style_display_contents()


if __name__ == "__main__":
    _app.run(port=7777)
