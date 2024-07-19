import os
import pickle
import tempfile
import uuid
import dash_bootstrap_components as dbc
import dash_uploader as du
from dash import Dash
from dash import Input
from dash import Output
from dash import clientside_callback
from dash import html


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED, dbc_css, dbc.icons.FONT_AWESOME])

# ------------------ Nav Bar ------------------ #
color_mode_switch = html.Span(
    [
        dbc.Label(className="fa fa-moon", html_for="color-mode-switch"),
        dbc.Switch(
            id="color-mode-switch",
            value=False,
            className="d-inline-block ms-1",
            persistence=True,
        ),
        dbc.Label(className="fa fa-sun", html_for="color-mode-switch"),
    ],
    className="p-2",
)

# Define the navigation bar
navbar = dbc.Row(
    dbc.Col(
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Doc", href="https://nplinker.github.io/nplinker/latest/")),
                dbc.NavItem(
                    dbc.NavLink("About", href="https://github.com/NPLinker/nplinker-webapp"),
                ),
                dbc.NavItem(
                    color_mode_switch,
                    className="mt-1 p-1",
                ),
            ],
            brand="NPLinker Webapp",
            brand_href="https://github.com/NPLinker/nplinker-webapp",
            color="primary",
            className="p-3 mb-2",
            dark=True,
        ),
    ),
)

# ------------------ Uploader ------------------ #
# Configure the upload folder
TEMP_DIR = tempfile.mkdtemp()
du.configure_upload(app, TEMP_DIR)

uploader = html.Div(
    [
        dbc.Row(
            dbc.Col(
                du.Upload(
                    id="dash-uploader",
                    text="Import Data",
                    text_completed="Uploaded: ",
                    filetypes=["pkl"],
                    upload_id=uuid.uuid1(),  # Unique session id
                    cancel_button=True,
                    max_files=1,
                ),
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(children="No file uploaded", id="dash-uploader-output", className="p-4"),
                className="d-flex justify-content-center",
            )
        ),
    ],
    className="p-5 ml-5 mr-5",
)

# ------------------ Tabs ------------------ #
# gm tab content
gm_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div()]),
        )
    )
)
# mg tab content
mg_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div()]),
        )
    ),
)
# tabs
tabs = dbc.Row(
    dbc.Col(
        dbc.Tabs(
            [
                dbc.Tab(
                    gm_content,
                    label="Genomics -> Metabolomics",
                    activeTabClassName="fw-bold",
                    disabled=True,
                    id="gm-tab",
                    className="disabled-tab",
                ),
                dbc.Tab(
                    mg_content,
                    label="Metabolomics -> Genomics",
                    activeTabClassName="fw-bold",
                    disabled=True,
                    id="mg-tab",
                    className="disabled-tab",
                ),
            ],
        ),
    ),
    className="p-5",
)

app.layout = dbc.Container([navbar, uploader, tabs], fluid=True, className="p-0")

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


@du.callback(
    id="dash-uploader",
    output=Output("dash-uploader-output", "children"),
)
def upload_data(status: du.UploadStatus):  # noqa: D103
    with open(status.latest_file, "rb") as f:
        pickle.load(f)
    return f"Successfully uploaded file `{os.path.basename(status.latest_file)}` of size {round(status.uploaded_size_mb, 2)} MB."


@app.callback(
    [Output("gm-tab", "disabled"), Output("mg-tab", "disabled")],
    [Input("dash-uploader-output", "children")],
    prevent_initial_call=True,
)
def enable_tabs(string):  # noqa: D103
    return False, False


# TODO: add tests

if __name__ == "__main__":
    app.run_server(debug=True)
