import dash_bootstrap_components as dbc
from dash import Dash
from dash import Input
from dash import Output
from dash import clientside_callback
from dash import html


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED, dbc_css, dbc.icons.FONT_AWESOME])

# Define the navigation bar
navbar = dbc.Row(
    dbc.Col(
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(
                    dbc.NavLink("Import Data", href="#")
                ),  # TODO: Add the import data button
                dbc.NavItem(dbc.NavLink("Doc", href="https://nplinker.github.io/nplinker/latest/")),
                dbc.NavItem(dbc.NavLink("About", href="https://github.com/nplinker/nplinker")),
            ],
            brand="NPLinker Dashboard",
            brand_href="https://github.com/NPLinker/nplinker-webapp",
            color="primary",
            className="p-4 mb-2",
            dark=True,
        ),
    ),
    className="mb-2",
)

color_mode_switch = html.Span(
    [
        dbc.Label(className="fa fa-moon", html_for="color-mode-switch"),
        dbc.Switch(
            id="color-mode-switch", value=False, className="d-inline-block ms-1", persistence=True
        ),
        dbc.Label(className="fa fa-sun", html_for="color-mode-switch"),
    ],
    className="p-4 position-absolute end-0 mt-2",
)

# Define the content area with tabs
gm_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div("Tab 1 Content", className="p-4 card-text")]),
        )
    )
)

mg_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div("Tab 2 Content", className="p-4 card-text")]),
        )
    )
)

tabs = dbc.Row(
    dbc.Col(
        dbc.Tabs(
            [
                dbc.Tab(
                    gm_content,
                    label="Genomics -> Metabolomics",
                    activeTabClassName="fw-bold",
                ),
                dbc.Tab(
                    mg_content,
                    label="Metabolomics -> Genomics",
                    activeTabClassName="fw-bold",
                ),
            ],
        ),
    ),
    className="p-4",
)

app.layout = dbc.Container([navbar, color_mode_switch, tabs], fluid=True, className="p-0")

clientside_callback(
    """
    (switchOn) => {
       document.documentElement.setAttribute('data-bs-theme', switchOn ? 'light' : 'dark');
       return window.dash_clientside.no_update
    }
    """,
    Output("color-mode-switch", "id"),
    Input("color-mode-switch", "value"),
)


if __name__ == "__main__":
    app.run_server(debug=True)
