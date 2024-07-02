import dash_bootstrap_components as dbc
from dash import Dash
from dash import html


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED, dbc_css])

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
    className="mb-5",
)

# Define the content area with tabs
gm_content = html.Div("Tab 1 Content", className="p-4 border")
mg_content = html.Div("Tab 2 Content", className="p-4 border")

# TODO: Improve the tabs stile (dbc or dcc?)
tabs = dbc.Row(
    dbc.Col(
        dbc.Tabs(
            [
                dbc.Tab(
                    gm_content,
                    label="Genomics -> Metabolomics",
                    # selected_style={"font-size": "20px", "background-color": "#f8f9fa"},
                ),
                dbc.Tab(
                    mg_content,
                    label="Metabolomics -> Genomics",
                    # selected_style={"font-size": "20px"},
                ),
            ]
        )
    ),
    className="p-4",
)


app.layout = dbc.Container([navbar, tabs], fluid=True, className="dbc p-0")

if __name__ == "__main__":
    app.run_server(debug=True)
