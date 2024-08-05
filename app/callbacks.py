import os
import pickle
import tempfile
import uuid
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
from dash import MATCH
from dash import Dash
from dash import Input
from dash import Output
from dash import State
from dash import clientside_callback
from dash import dcc
from dash import html


dash._dash_renderer._set_react_version("18.2.0")


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED, dbc_css, dbc.icons.FONT_AWESOME])
# Configure the upload folder
TEMP_DIR = tempfile.mkdtemp()
du.configure_upload(app, TEMP_DIR)

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
    output=[Output("dash-uploader-output", "children"), Output("file-store", "data")],
)
def upload_data(status: du.UploadStatus):  # noqa: D103
    if status.is_completed:
        latest_file = status.latest_file
        with open(status.latest_file, "rb") as f:
            pickle.load(f)
        return (
            f"Successfully uploaded: {os.path.basename(latest_file)} [{round(status.uploaded_size_mb, 2)} MB]",
            str(latest_file),
        )
    return "No file uploaded", None


@app.callback(
    [
        Output("gm-tab", "disabled"),
        Output("gm-accordion-control", "disabled"),
        Output("mg-tab", "disabled"),
    ],
    [Input("file-store", "data")],
    prevent_initial_call=True,
)
def disable_tabs(file_name):  # noqa: D103
    if file_name is None:
        # Disable the tabs
        return True, True, True
    # Enable the tabs
    return False, False, False


# Define another callback to access the stored file path and read the file
@app.callback(
    Output("file-content-mg", "children"),
    [Input("file-store", "data")],
)
def display_file_contents(file_path):  # noqa: D103
    if file_path is not None:
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        # Process and display the data as needed
        content = f"File contents: {data[0][:2]}"
        return content  # Display same content in both tabs
    return "No data available"


@app.callback(
    Output("block-store", "data"), Input("add-button", "n_clicks"), State("block-store", "data")
)
def add_block(n_clicks, blocks_data):  # noqa: D103
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    # Create a unique ID for the new block
    new_block_id = str(uuid.uuid4())

    blocks_data.append(new_block_id)
    return blocks_data


@app.callback(Output("blocks-container", "children"), Input("block-store", "data"))
def display_blocks(blocks_data):  # noqa: D103
    blocks = []

    for block_id in blocks_data:
        blocks.append(
            dmc.Grid(
                id={"type": "gm-block", "index": block_id},
                children=[
                    dmc.GridCol(
                        dbc.Button(
                            [html.I(className="fas fa-plus")],
                            className="btn-primary",
                        ),
                        span=1,
                    ),
                    dmc.GridCol(
                        dcc.Dropdown(
                            options=[
                                {"label": "GCF ID", "value": "GCF_ID"},
                                {"label": "BiG-SCAPE Class", "value": "BSC_CLASS"},
                            ],
                            value="GCF_ID",
                            placeholder="Enter one or more GCF IDs",
                            id={"type": "gm-dropdown-menu", "index": block_id},
                            clearable=False,
                        ),
                        span=6,
                    ),
                    dmc.GridCol(
                        dmc.TextInput(
                            id={"type": "gm-dropdown-input", "index": block_id},
                            placeholder="",
                            className="custom-textinput",
                        ),
                        span=5,
                    ),
                ],
                gutter="md",
            )
        )

    return blocks


@app.callback(
    Output({"type": "gm-dropdown-input", "index": MATCH}, "placeholder"),
    Output({"type": "gm-dropdown-input", "index": MATCH}, "value"),
    Input({"type": "gm-dropdown-menu", "index": MATCH}, "value"),
)
def update_placeholder(selected_value):  # noqa: D103
    if selected_value == "GCF_ID":
        return "Enter one or more GCF IDs", ""
    elif selected_value == "BSC_CLASS":
        return "Enter one or more GCF BiG-SCAPE classes", ""
    return "", ""
