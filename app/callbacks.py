import os
import pickle
import tempfile
import uuid
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
from dash import ALL
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
    Output("blocks-id", "data"),
    Input({"type": "gm-add-button", "index": ALL}, "n_clicks"),
    State("blocks-id", "data"),
)
def add_block(n_clicks, blocks_id):  # noqa: D103
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate
    # Create a unique ID for the new block
    new_block_id = str(uuid.uuid4())
    blocks_id.append(new_block_id)
    return blocks_id


@app.callback(
    Output("blocks-container", "children"),
    Input("blocks-id", "data"),
    Input("blocks-container", "children"),
)
def display_blocks(blocks_id, blocks):  # noqa: D103
    # Start with one block in the layout and then add additional blocks dynamically
    blocks = [
        dmc.Grid(
            id={"type": "gm-block", "index": block_id},
            children=[
                dmc.GridCol(
                    dbc.Button(
                        [html.I(className="fas fa-plus")],
                        id={"type": "gm-add-button", "index": block_id},
                        className="btn-primary",
                        style={
                            "display": "block" if i == len(blocks_id) - 1 else "none"
                        },  # Show button only on the latest block
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
        for i, block_id in enumerate(blocks_id)
    ]
    return blocks


@app.callback(
    Output({"type": "gm-dropdown-input", "index": MATCH}, "placeholder"),
    Output({"type": "gm-dropdown-input", "index": MATCH}, "value"),
    Input({"type": "gm-dropdown-menu", "index": MATCH}, "value"),
)
def update_placeholder(selected_value):  # noqa: D103
    if selected_value == "GCF_ID":
        return "1, 2, 3, ...", ""
    elif selected_value == "BSC_CLASS":
        return "Enter one or more GCF BiG-SCAPE classes", ""
    return "", ""
