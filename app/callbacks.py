import json
import os
import pickle
import tempfile
import uuid
from pathlib import Path
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
def process_uploaded_data(file_path: Path | str | None) -> str | None:
    """Process the uploaded pickle file and store the processed data.

    Args:
        file_path: Path to the uploaded pickle file.

    Returns:
        JSON string of processed data or None if processing fails.
    """
    if file_path is None:
        return None

    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        # Extract and process the necessary data
        bgcs, gcfs, *_ = data

        def process_bgc_class(bgc_class: tuple[str, ...] | None) -> list[str]:
            if bgc_class is None:
                return ["Unknown"]
            return list(bgc_class)  # Convert tuple to list

        # Create a dictionary to map BGC to its class
        bgc_to_class = {bgc.id: process_bgc_class(bgc.mibig_bgc_class) for bgc in bgcs}

        processed_data: dict[str, Any] = {"n_bgcs": {}, "gcf_data": []}

        for gcf in gcfs:
            gcf_bgc_classes = [cls for bgc in gcf.bgcs for cls in bgc_to_class[bgc.id]]
            bgc_data = [
                (bgc.id, bgc.smiles[0] if bgc.smiles and bgc.smiles[0] is not None else "N/A")
                for bgc in gcf.bgcs
            ]
            bgc_data.sort(key=lambda x: x[0])
            bgc_ids, bgc_smiles = zip(*bgc_data)
            strains = [s.id for s in gcf.strains._strains]
            strains.sort()
            processed_data["gcf_data"].append(
                {
                    "GCF ID": gcf.id,
                    "# BGCs": len(gcf.bgcs),
                    "BGC Classes": list(set(gcf_bgc_classes)),  # Using set to get unique classes
                    "BGC IDs": list(bgc_ids),
                    "BGC smiles": list(bgc_smiles),
                    "strains": strains,
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
    file_path: Path | str | None,
) -> tuple[bool, bool, dict, dict[str, str], bool, list[str], list[dmc.Grid]]:
    """Manage tab states and reset blocks based on file upload status.

    Args:
        file_path: The name of the uploaded file, or None if no file is uploaded.

    Returns:
        Tuple containing boolean values for disabling tabs, styles, and new block data.
    """
    if file_path is None:
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
        A Grid component with nested elements.
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
                span=2,
            ),
            dmc.GridCol(
                dcc.Dropdown(
                    options=GM_DROPDOWN_MENU_OPTIONS,
                    value="GCF_ID",
                    id={"type": "gm-dropdown-menu", "index": block_id},
                    clearable=False,
                ),
                span=4,
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
                span=6,
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
def gm_plot(stored_data: str | None) -> tuple[dict | go.Figure, dict, str]:
    """Create a bar plot based on the processed data.

    Args:
        stored_data: JSON string of processed data or None.

    Returns:
        Tuple containing the plot figure, style, and a status message.
    """
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
                    html.Div(
                        [
                            dbc.Button(
                                [html.I(className="fas fa-plus")],
                                id={"type": "gm-add-button", "index": new_block_id},
                                className="btn-primary",
                            ),
                            html.Label(
                                "OR",
                                id={"type": "gm-or-label", "index": new_block_id},
                                className="ms-2 px-2 py-1 rounded",
                                style={
                                    "color": "green",
                                    "backgroundColor": "#f0f0f0",
                                    "display": "inline-block",
                                    "position": "absolute",
                                    "left": "50px",  # Adjust based on button width
                                    "top": "50%",
                                    "transform": "translateY(-50%)",
                                },
                            ),
                        ],
                        style={"position": "relative", "height": "38px"},
                    ),
                    span=2,
                ),
                dmc.GridCol(
                    dcc.Dropdown(
                        options=GM_DROPDOWN_MENU_OPTIONS,
                        value="GCF_ID",
                        id={"type": "gm-dropdown-menu", "index": new_block_id},
                        clearable=False,
                    ),
                    span=4,
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
                    span=6,
                ),
            ],
            gutter="md",
        )

        # Hide the add button and OR label on the previous last block
        if len(existing_blocks) == 1:
            existing_blocks[-1]["props"]["children"][0]["props"]["children"]["props"]["style"] = {
                "display": "none"
            }
        else:
            existing_blocks[-1]["props"]["children"][0]["props"]["children"]["props"]["children"][
                0
            ]["props"]["style"] = {"display": "none"}

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


def apply_filters(
    df: pd.DataFrame,
    dropdown_menus: list[str],
    text_inputs: list[str],
    bgc_class_dropdowns: list[list[str]],
) -> pd.DataFrame:
    """Apply filters to the DataFrame based on user inputs.

    Args:
        df: The input DataFrame.
        dropdown_menus: List of selected dropdown menu options.
        text_inputs: List of text inputs for GCF IDs.
        bgc_class_dropdowns: List of selected BGC classes.

    Returns:
        Filtered DataFrame.
    """
    masks = []

    for menu, text_input, bgc_classes in zip(dropdown_menus, text_inputs, bgc_class_dropdowns):
        if menu == "GCF_ID" and text_input:
            gcf_ids = [id.strip() for id in text_input.split(",") if id.strip()]
            if gcf_ids:
                mask = df["GCF ID"].astype(str).isin(gcf_ids)
                masks.append(mask)
        elif menu == "BGC_CLASS" and bgc_classes:
            mask = df["BGC Classes"].apply(
                lambda x: any(bc.lower() in [y.lower() for y in x] for bc in bgc_classes)
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
    Output("gm-table", "tooltip_data"),
    Output("gm-table-card-body", "style"),
    Output("gm-table", "selected_rows", allow_duplicate=True),
    Output("select-all-checkbox", "value"),
    Input("processed-data-store", "data"),
    Input("apply-filters-button", "n_clicks"),
    State({"type": "gm-dropdown-menu", "index": ALL}, "value"),
    State({"type": "gm-dropdown-ids-text-input", "index": ALL}, "value"),
    State({"type": "gm-dropdown-bgc-class-dropdown", "index": ALL}, "value"),
    State("select-all-checkbox", "value"),
    prevent_initial_call=True,
)
def update_datatable(
    processed_data: str | None,
    n_clicks: int | None,
    dropdown_menus: list[str],
    text_inputs: list[str],
    bgc_class_dropdowns: list[list[str]],
    checkbox_value: list | None,
) -> tuple[list[dict], list[dict], list[dict], dict, list, list]:
    """Update the DataTable based on processed data and applied filters when the button is clicked.

    Args:
        processed_data: JSON string of processed data.
        n_clicks: Number of times the Apply Filters button has been clicked.
        dropdown_menus: List of selected dropdown menu options.
        text_inputs: List of text inputs for GCF IDs.
        bgc_class_dropdowns: List of selected BGC classes.
        checkbox_value: Current value of the select-all checkbox.

    Returns:
        Tuple containing table data, column definitions, tooltips data, style, empty selected rows, and updated checkbox value.
    """
    if processed_data is None:
        return [], [], [], {"display": "none"}, [], []

    try:
        data = json.loads(processed_data)
        df = pd.DataFrame(data["gcf_data"])
    except (json.JSONDecodeError, KeyError, pd.errors.EmptyDataError):
        return [], [], [], {"display": "none"}, [], []

    if ctx.triggered_id == "apply-filters-button":
        # Apply filters only when the button is clicked
        filtered_df = apply_filters(df, dropdown_menus, text_inputs, bgc_class_dropdowns)
        # Reset the checkbox when filters are applied
        new_checkbox_value = []
    else:
        # On initial load or when processed data changes, show all data
        filtered_df = df
        new_checkbox_value = checkbox_value if checkbox_value is not None else []

    # Prepare the data for display
    display_df = filtered_df[["GCF ID", "# BGCs", "BGC IDs", "BGC smiles", "strains"]]
    display_data = display_df[["GCF ID", "# BGCs"]].to_dict("records")

    # Prepare tooltip data
    tooltip_data = []
    for _, row in display_df.iterrows():
        bgc_ids_smiles_markdown = "| BGC IDs | SMILES |\n|---------|--------|\n" + "\n".join(
            [f"| {id} | {smiles} |" for id, smiles in zip(row["BGC IDs"], row["BGC smiles"])]
        )
        strains_markdown = "| Strains |\n|----------|\n" + "\n".join(
            [f"| {strain} |" for strain in row["strains"]]
        )

        tooltip_data.append(
            {
                "# BGCs": {"value": bgc_ids_smiles_markdown, "type": "markdown"},
                "GCF ID": {"value": strains_markdown, "type": "markdown"},
            }
        )

    columns = [
        {"name": "GCF ID", "id": "GCF ID"},
        {"name": "# BGCs", "id": "# BGCs", "type": "numeric"},
    ]

    return display_data, columns, tooltip_data, {"display": "block"}, [], new_checkbox_value


@app.callback(
    Output("gm-table", "selected_rows", allow_duplicate=True),
    Input("select-all-checkbox", "value"),
    State("gm-table", "data"),
    State("gm-table", "derived_virtual_data"),
    prevent_initial_call=True,
)
def toggle_selection(
    value: list | None,
    original_rows: list,
    filtered_rows: list | None,
) -> list:
    """Toggle between selecting all rows and deselecting all rows in the current view of a Dash DataTable.

    Args:
        value: Value of the select-all checkbox.
        original_rows: All rows in the table.
        filtered_rows: Rows visible after filtering, or None if no filter is applied.

    Returns:
        List of indices of selected rows after toggling.
    """
    is_checked = value and "disabled" in value

    if filtered_rows is None:
        # No filtering applied, toggle all rows
        return list(range(len(original_rows))) if is_checked else []
    else:
        # Filtering applied, toggle only visible rows
        return (
            [i for i, row in enumerate(original_rows) if row in filtered_rows] if is_checked else []
        )


@app.callback(
    Output("gm-table-output1", "children"),
    Output("gm-table-output2", "children"),
    Input("gm-table", "derived_virtual_data"),
    Input("gm-table", "derived_virtual_selected_rows"),
)
def select_rows(rows: list[dict[str, Any]], selected_rows: list[int] | None) -> tuple[str, str]:
    """Display the total number of rows and the number of selected rows in the table.

    Args:
        rows: List of row data from the DataTable.
        selected_rows: Indices of selected rows.

    Returns:
        Strings describing total rows and selected rows.
    """
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
