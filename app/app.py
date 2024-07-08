import base64
import datetime
import io
import pickle
import dash_bootstrap_components as dbc
from dash import Dash
from dash import Input
from dash import Output
from dash import State
from dash import clientside_callback
from dash import dcc
from dash import html


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED, dbc_css, dbc.icons.FONT_AWESOME])

# Define the navigation bar
navbar = dbc.Row(
    dbc.Col(
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(
                    dcc.Upload(
                        id="upload-data",
                        children=dbc.Button("Import Data"),
                        style={"margin-top": "0.1rem"},
                        multiple=False,
                    )
                ),
                dbc.NavItem(dbc.NavLink("Doc", href="https://nplinker.github.io/nplinker/latest/")),
                dbc.NavItem(
                    dbc.NavLink("About", href="https://github.com/NPLinker/nplinker-webapp")
                ),
            ],
            brand="NPLinker Webapp",
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
            dbc.CardBody([dbc.Row(html.Div(id="output-data-upload"))]),
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


# Function to parse the contents of the uploaded file
def parse_contents(contents, filename):  # noqa: D103
    try:
        if not contents:
            return html.Div(["No contents uploaded."])
        _, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        if filename.endswith(".pkl"):
            data = pickle.load(io.BytesIO(decoded))
            bgcs, gcfs, spectra, mfs, strains, links = data
        else:
            return html.Div(["Unsupported file format."])
    except Exception as e:
        return html.Div([f"There was an error processing this file: {e}"])

    return html.Div(
        [
            html.H5(filename),
            html.H6(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            html.Hr(),  # horizontal line
            html.Div("Raw Content"),
            html.Pre(
                contents[:200] + "...", style={"whiteSpace": "pre-wrap", "wordBreak": "break-all"}
            ),
        ]
    )


@app.callback(
    Output("output-data-upload", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_output(contents, filename):  # noqa: D103
    if contents is not None:
        children = parse_contents(contents, filename)
        return children
    return html.Div(["No file uploaded."])


if __name__ == "__main__":
    app.run_server(debug=True)
