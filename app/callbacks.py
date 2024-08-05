import os
import pickle
import tempfile
import dash
import dash_bootstrap_components as dbc
import dash_uploader as du
from dash import Dash
from dash import Input
from dash import Output
from dash import clientside_callback


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
    Output("gm-dropdown-input", "placeholder"),
    Output("gm-dropdown-input", "value"),
    [Input("gm-dropdown-menu", "value"), Input("gm-dropdown-input", "value")],
    allow_duplicate=True,
)
def update_placeholder(selected_dropdown, input_value):  # noqa: D103
    if selected_dropdown == "GCF_ID":
        placeholder = "Enter one or more GCF IDs"
    elif selected_dropdown == "BSC_CLASS":
        placeholder = "Enter one or more GCF BiG-SCAPE classes"

    # Clear the text input when dropdown selection changes
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "gm-dropdown-menu.value":
        input_value = ""

    return placeholder, input_value
