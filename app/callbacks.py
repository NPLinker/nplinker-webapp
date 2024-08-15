import json
import os
import pickle
import tempfile
import uuid
from typing import Any
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
import pandas as pd
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


dash._dash_renderer._set_react_version("18.2.0")  # type: ignore


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
    Output("processed-data-store", "data"), Input("file-store", "data"), prevent_initial_call=True
)
def process_uploaded_data(file_path):
    if file_path is None:
        return None

    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        # Extract and process the necessary data
        bgcs, gcfs, *_ = data

        def process_bgc_class(bgc_class):
            if bgc_class is None:
                return ["Unknown"]
            return list(bgc_class)  # Convert tuple to list

        # Create a dictionary to map BGC to its class
        bgc_to_class = {bgc.id: process_bgc_class(bgc.mibig_bgc_class) for bgc in bgcs}

        processed_data = {"n_bgcs": {}, "gcf_data": []}

        for gcf in gcfs:
            gcf_bgc_classes = [cls for bgc in gcf.bgcs for cls in bgc_to_class[bgc.id]]
            processed_data["gcf_data"].append(
                {
                    "GCF ID": gcf.id,
                    "# BGCs": len(gcf.bgcs),
                    "BGC Classes": list(set(gcf_bgc_classes)),  # Using set to get unique classes
                }
            )

            if len(gcf.bgcs) not in processed_data["n_bgcs"]:
                processed_data["n_bgcs"][len(gcf.bgcs)] = []
            processed_data["n_bgcs"][len(gcf.bgcs)].append(gcf.id)

        return json.dumps(processed_data)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None


@app.callback(
    [
        Output("gm-tab", "disabled"),
        Output("gm-accordion-control", "disabled"),
        Output("gm-table-card-header", "style"),
        Output("gm-table-card-body", "style", allow_duplicate=True),
        Output("mg-tab", "disabled"),
        Output("blocks-id", "data", allow_duplicate=True),
        Output("blocks-container", "children", allow_duplicate=True),
    ],
    [Input("file-store", "data")],
    prevent_initial_call=True,
)
def disable_tabs_and_reset_blocks(
    file_name: str | None,
) -> tuple[bool, bool, dict, dict[str, str], bool, list[str], list[dmc.Grid]]:
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
        return True, True, {}, {"display": "block"}, True, [], []

    # Enable the tabs and reset blocks
    initial_block_id = [str(uuid.uuid4())]
    new_blocks = [create_initial_block(initial_block_id[0])]

    return False, False, {}, {"display": "block"}, False, initial_block_id, new_blocks


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
    [Input("processed-data-store", "data")],
)
def gm_plot(stored_data):  # noqa: D103
    if stored_data is None:
        return {}, {"display": "none"}, "No data available"
    data = json.loads(stored_data)
    n_bgcs = data["n_bgcs"]

    x_values = sorted(map(int, n_bgcs.keys()))
    y_values = [len(n_bgcs[str(x)]) for x in x_values]
    hover_texts = [f"GCF IDs: {', '.join(n_bgcs[str(x)])}" for x in x_values]

    # Adjust bar width based on number of data points
    bar_width = 0.4 if len(x_values) <= 5 else None
    # Create the bar plot
    fig = go.Figure(
        data=[
            go.Bar(
                x=x_values,
                y=y_values,
                text=hover_texts,
                hoverinfo="text",
                textposition="none",
                width=bar_width,
            )
        ]
    )
    # Update layout
    fig.update_layout(
        xaxis_title="# BGCs",
        yaxis_title="# GCFs",
        xaxis=dict(type="category"),
    )
    return fig, {"display": "block"}, "Data loaded and plotted!!"


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


def apply_filters(df, dropdown_menus, text_inputs, bgc_class_dropdowns):
    masks = []

    for menu, text_input, bgc_classes in zip(dropdown_menus, text_inputs, bgc_class_dropdowns):
        if menu == "GCF_ID" and text_input:
            gcf_ids = [id.strip() for id in text_input.split(",") if id.strip()]
            if gcf_ids:
                mask = df["GCF ID"].astype(str).isin(gcf_ids)
                masks.append(mask)
        elif menu == "BGC_CLASS" and bgc_classes:
            mask = df["BGC Classes"].apply(
                lambda x: any(bgc_class in x for bgc_class in bgc_classes)
            )
            masks.append(mask)

    if masks:
        # Combine all masks with OR operation
        final_mask = pd.concat(masks, axis=1).any(axis=1)
        return df[final_mask]
    else:
        return df


@app.callback(
    Output("gm-table", "data"),
    Output("gm-table", "columns"),
    Output("gm-table-card-body", "style"),
    Input("processed-data-store", "data"),
    Input({"type": "gm-dropdown-menu", "index": ALL}, "value"),
    Input({"type": "gm-dropdown-ids-text-input", "index": ALL}, "value"),
    Input({"type": "gm-dropdown-bgc-class-dropdown", "index": ALL}, "value"),
)
def update_datatable(processed_data, dropdown_menus, text_inputs, bgc_class_dropdowns):
    if processed_data is None:
        return [], [], {"display": "none"}

    data = json.loads(processed_data)
    df = pd.DataFrame(data["gcf_data"])

    # Apply filters
    filtered_df = apply_filters(df, dropdown_menus, text_inputs, bgc_class_dropdowns)

    display_df = filtered_df[["GCF ID", "# BGCs"]]

    columns = [
        {"name": i, "id": i, "deletable": False, "selectable": False} for i in display_df.columns
    ]

    return display_df.to_dict("records"), columns, {"display": "block"}


@app.callback(
    [Output("gm-table", "selected_rows")],
    [Input("gm-rows-selection-button", "n_clicks")],
    [
        State("gm-table", "data"),
        State("gm-table", "derived_virtual_data"),
        State("gm-table", "derived_virtual_selected_rows"),
    ],
)
def toggle_selection(
    n_clicks: int, original_rows: list, filtered_rows: list, selected_rows: list
) -> list:
    """Toggle between selecting all rows and deselecting all rows in a Dash DataTable.

    Args:
        n_clicks: Number of button clicks (unused).
        original_rows: All rows in the table.
        filtered_rows: Rows visible after filtering.
        selected_rows: Currently selected row indices.

    Returns:
        Indices of selected rows after toggling.

    Raises:
        PreventUpdate: If filtered_rows is None.
    """
    if filtered_rows is None:
        raise dash.exceptions.PreventUpdate

    if not selected_rows or len(selected_rows) < len(filtered_rows):
        # If no rows are selected or not all rows are selected, select all filtered rows
        selected_ids = [row for row in filtered_rows]
        return [[i for i, row in enumerate(original_rows) if row in selected_ids]]
    else:
        # If all rows are selected, deselect all
        return [[]]


@app.callback(
    Output("gm-table-output1", "children"),
    Output("gm-table-output2", "children"),
    Input("gm-table", "derived_virtual_data"),
    Input("gm-table", "derived_virtual_selected_rows"),
)
def select_rows(rows, selected_rows):
    """Display the total number of rows and the number of selected rows in the table."""
    if not rows:
        return "No data available.", "No rows selected."

    df = pd.DataFrame(rows)

    if selected_rows is None:
        selected_rows = []

    selected_rows_data = df.iloc[selected_rows]

    # to be removed later when the scoring part will be implemented
    output1 = f"Total rows: {len(df)}"
    output2 = f"Selected rows: {len(selected_rows)}\nSelected GCF IDs: {', '.join(selected_rows_data['GCF ID'].astype(str))}"

    return output1, output2
