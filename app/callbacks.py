import os
import pickle
import dash_uploader as du
from dash import Input
from dash import Output
from dash import clientside_callback


def register_callbacks(app):  # noqa: D103
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
        [Output("gm-tab", "disabled"), Output("mg-tab", "disabled")],
        [Input("file-store", "data")],
        prevent_initial_call=True,
    )
    def disable_tabs(file_name):  # noqa: D103
        if file_name is None:
            # Disable the tabs
            return True, True
        # Enable the tabs
        return False, False

    # Define another callback to access the stored file path and read the file
    @app.callback(
        [Output("file-content-gm", "children"), Output("file-content-mg", "children")],
        [Input("file-store", "data")],
    )
    def display_file_contents(file_path):  # noqa: D103
        if file_path is not None:
            with open(file_path, "rb") as f:
                data = pickle.load(f)
            # Process and display the data as needed
            content = f"File contents: {data[0][:2]}"
            return content, content  # Display same content in both tabs
        return "No data available", "No data available"
