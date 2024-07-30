import os
import pickle
import tempfile
import dash
import dash_bootstrap_components as dbc
import dash_uploader as du
from dash import Dash
from dash import Input
from dash import Output
from dash import State
from dash import clientside_callback


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
        Output("gm-filter-button", "disabled"),
        Output("gcf-ids-dropdown-menu", "disabled"),
        Output("gcf-ids-dropdown-input", "disabled"),
        Output("gcf-bigscape-dropdown-menu", "disabled"),
        Output("gcf-bigscape-dropdown-input", "disabled"),
        Output("mg-tab", "disabled"),
    ],
    [Input("file-store", "data")],
    prevent_initial_call=True,
)
def disable_tabs(file_name):  # noqa: D103
    if file_name is None:
        # Disable the tabs
        return True, True, True, True, True, True, True
    # Enable the tabs
    return False, False, False, False, False, False, False


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
    Output("gm-filter-collapse", "is_open"),
    [Input("gm-filter-button", "n_clicks")],
    [State("gm-filter-collapse", "is_open")],
)
def toggle_gm_filter_collapse(n, is_open):  # noqa: D103
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("gcf-ids-dropdown-input", "value"),
    Output("gcf-bigscape-dropdown-input", "value"),
    [
        Input("gcf-ids-dropdown-input", "value"),
        Input("gcf-ids-dropdown-clear", "n_clicks"),
        Input("gcf-bigscape-dropdown-input", "value"),
        Input("gcf-bigscape-dropdown-clear", "n_clicks"),
    ],
)
def gm_filter(gcf_ids, gcf_ids_clear, gcf_bigscape, gcf_bigscape_clear):  # noqa: D103
    ctx = dash.callback_context

    if not ctx.triggered:
        return "", ""
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "gcf-ids-dropdown-clear":
        return "", gcf_bigscape
    elif button_id == "gcf-ids-dropdown-input":
        return gcf_ids, gcf_bigscape
    elif button_id == "gcf-bigscape-dropdown-clear":
        return gcf_ids, ""
    elif button_id == "gcf-bigscape-dropdown-input":
        return gcf_ids, gcf_bigscape
