import os
import pickle
import tempfile
import uuid
from typing import Any
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
import plotly.graph_objects as go
from config import GM_DROPDOWN_BGC_CLASS_OPTIONS
from config import GM_DROPDOWN_MENU_OPTIONS
from dash import ALL
from dash import MATCH
from dash import Dash
from dash import Input
from dash import Output
from dash import State
from dash import callback_context as ctx
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
def upload_data(status: du.UploadStatus) -> tuple[str, str | None]:
    """Handle file upload and validate pickle files.

    Args:
        status: The upload status object.

    Returns:
        A tuple containing a message string and the file path (if successful).
    """
    if status.is_completed:
        latest_file = status.latest_file
        try:
            with open(status.latest_file, "rb") as f:
                pickle.load(f)
            return (
                f"Successfully uploaded: {os.path.basename(latest_file)} [{round(status.uploaded_size_mb, 2)} MB]",
                str(latest_file),
            )
        except (pickle.UnpicklingError, EOFError, AttributeError):
            return f"Error: {os.path.basename(latest_file)} is not a valid pickle file.", None
        except Exception as e:
            # Handle any other unexpected errors
            return f"Error uploading file: {str(e)}", None
    return "No file uploaded", None


@app.callback(
    [
        Output("gm-tab", "disabled"),
        Output("gm-accordion-control", "disabled"),
        Output("mg-tab", "disabled"),
        Output("blocks-id", "data", allow_duplicate=True),
        Output("blocks-container", "children", allow_duplicate=True),
    ],
    [Input("file-store", "data")],
    prevent_initial_call=True,
)
def disable_tabs_and_reset_blocks(
    file_name: str | None,
) -> tuple[bool, bool, bool, list[str], list[dict[str, Any]]]:
    """Manage tab states and reset blocks based on file upload status.

    Args:
        file_name: The name of the uploaded file, or None if no file is uploaded.

    Returns:
        A tuple containing:
        - Boolean values for disabling gm-tab, gm-accordion-control, and mg-tab.
        - A list with a single block ID.
        - A list with a single block component.
    """
    if file_name is None:
        # Disable the tabs, don't change blocks
        return True, True, True, [], []

    # Enable the tabs and reset blocks
    initial_block_id = [str(uuid.uuid4())]
    new_blocks = [create_initial_block(initial_block_id[0])]

    return False, False, False, initial_block_id, new_blocks


def create_initial_block(block_id: str) -> dmc.Grid:
    """Create the initial block component with the given ID.

    Args:
        block_id: A unique identifier for the block.

    Returns:
        A dictionary representing a dmc.Grid component with nested elements.
    """
    return dmc.Grid(
        id={"type": "gm-block", "index": block_id},
        children=[
            dmc.GridCol(
                dbc.Button(
                    [html.I(className="fas fa-plus")],
                    id={"type": "gm-add-button", "index": block_id},
                    className="btn-primary",
                ),
                span=1,
            ),
            dmc.GridCol(
                dcc.Dropdown(
                    options=GM_DROPDOWN_MENU_OPTIONS,
                    value="GCF_ID",
                    id={"type": "gm-dropdown-menu", "index": block_id},
                    clearable=False,
                ),
                span=6,
            ),
            dmc.GridCol(
                [
                    dmc.TextInput(
                        id={"type": "gm-dropdown-ids-text-input", "index": block_id},
                        placeholder="1, 2, 3, ...",
                        className="custom-textinput",
                    ),
                    dcc.Dropdown(
                        id={"type": "gm-dropdown-bgc-class-dropdown", "index": block_id},
                        options=GM_DROPDOWN_BGC_CLASS_OPTIONS,
                        multi=True,
                        style={"display": "none"},
                    ),
                ],
                span=5,
            ),
        ],
        gutter="md",
    )


@app.callback(
    Output("gm-graph", "figure"),
    Output("gm-graph", "style"),
    Output("file-content-mg", "children"),
    [Input("file-store", "data")],
)
def gm_plot(file_path):  # noqa: D103
    if file_path is not None:
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        # Process and display the data as needed
        _, gcfs, _, _, _, _ = data
        n_bgcs = {}
        for gcf in gcfs:
            n = len(gcf.bgcs)
            if n not in n_bgcs:
                n_bgcs[n] = [gcf.id]
            else:
                n_bgcs[n].append(gcf.id)
        x_values = list(n_bgcs.keys())
        x_values.sort()
        y_values = [len(n_bgcs[x]) for x in x_values]
        hover_texts = [f"GCF IDs: {', '.join(n_bgcs[x])}" for x in x_values]
        # Adjust bar width based on number of data points
        if len(x_values) <= 5:
            bar_width = 0.4
        else:
            bar_width = None
        # Create the bar plot
        fig = go.Figure(
            data=[
                go.Bar(
                    x=x_values,
                    y=y_values,
                    text=hover_texts,
                    hoverinfo="text",
                    textposition="none",
                    width=bar_width,  # Set the bar width
                )
            ]
        )
        # Update layout
        fig.update_layout(
            xaxis_title="# BGCs",
            yaxis_title="# GCFs",
            xaxis=dict(type="category"),
        )
        return fig, {"display": "block"}, "uploaded!!"
    return {}, {"display": "none"}, "No data available"


@app.callback(
    Output("blocks-id", "data"),
    Input({"type": "gm-add-button", "index": ALL}, "n_clicks"),
    State("blocks-id", "data"),
)
def add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
    """Add a new block to the layout when the add button is clicked.

    Args:
        n_clicks: List of number of clicks for each add button.
        blocks_id: Current list of block IDs.

    Returns:
        Updated list of block IDs.
    """
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate
    # Create a unique ID for the new block
    new_block_id = str(uuid.uuid4())
    blocks_id.append(new_block_id)
    return blocks_id


@app.callback(
    Output("blocks-container", "children"),
    Input("blocks-id", "data"),
    State("blocks-container", "children"),
)
def display_blocks(blocks_id: list[str], existing_blocks: list[dmc.Grid]) -> list[dmc.Grid]:
    """Display the blocks for the input block IDs.

    Args:
        blocks_id: List of block IDs.
        existing_blocks: Current list of block components.

    Returns:
        Updated list of block components.
    """
    if len(blocks_id) > 1:
        new_block_id = blocks_id[-1]

        new_block = dmc.Grid(
            id={"type": "gm-block", "index": new_block_id},
            children=[
                dmc.GridCol(
                    dbc.Button(
                        [html.I(className="fas fa-plus")],
                        id={"type": "gm-add-button", "index": new_block_id},
                        className="btn-primary",
                    ),
                    span=1,
                ),
                dmc.GridCol(
                    dcc.Dropdown(
                        options=GM_DROPDOWN_MENU_OPTIONS,
                        value="GCF_ID",
                        id={"type": "gm-dropdown-menu", "index": new_block_id},
                        clearable=False,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    [
                        dmc.TextInput(
                            id={"type": "gm-dropdown-ids-text-input", "index": new_block_id},
                            placeholder="1, 2, 3, ...",
                            className="custom-textinput",
                        ),
                        dcc.Dropdown(
                            id={"type": "gm-dropdown-bgc-class-dropdown", "index": new_block_id},
                            options=GM_DROPDOWN_BGC_CLASS_OPTIONS,
                            multi=True,
                            style={"display": "none"},
                        ),
                    ],
                    span=5,
                ),
            ],
            gutter="md",
        )

        # Hide the add button on the previous last block
        existing_blocks[-1]["props"]["children"][0]["props"]["children"]["props"]["style"] = {
            "display": "none"
        }

        return existing_blocks + [new_block]
    return existing_blocks


@app.callback(
    Output({"type": "gm-dropdown-ids-text-input", "index": MATCH}, "style"),
    Output({"type": "gm-dropdown-bgc-class-dropdown", "index": MATCH}, "style"),
    Output({"type": "gm-dropdown-ids-text-input", "index": MATCH}, "placeholder"),
    Output({"type": "gm-dropdown-bgc-class-dropdown", "index": MATCH}, "placeholder"),
    Output({"type": "gm-dropdown-ids-text-input", "index": MATCH}, "value"),
    Output({"type": "gm-dropdown-bgc-class-dropdown", "index": MATCH}, "value"),
    Input({"type": "gm-dropdown-menu", "index": MATCH}, "value"),
)
def update_placeholder(
    selected_value: str,
) -> tuple[dict[str, str], dict[str, str], str, str, str, list[Any]]:
    """Update the placeholder text and style of input fields based on the dropdown selection.

    Args:
        selected_value: The value selected in the dropdown menu.

    Returns:
        A tuple containing style, placeholder, and value updates for the input fields.
    """
    if not ctx.triggered:
        # Callback was not triggered by user interaction, don't change anything
        raise dash.exceptions.PreventUpdate
    if selected_value == "GCF_ID":
        return {"display": "block"}, {"display": "none"}, "1, 2, 3, ...", "", "", []
    elif selected_value == "BGC_CLASS":
        return (
            {"display": "none"},
            {"display": "block"},
            "",
            "Select one or more BGC classes",
            "",
            [],
        )
    else:
        # This case should never occur due to the Literal type, but it satisfies mypy
        return {"display": "none"}, {"display": "none"}, "", "", "", []
