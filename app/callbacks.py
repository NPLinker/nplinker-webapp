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
from config import GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS
from config import GM_FILTER_DROPDOWN_MENU_OPTIONS
from config import GM_SCORING_DROPDOWN_MENU_OPTIONS
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
    Output("processed-data-store", "data"),
    Output("processed-links-store", "data"),
    Input("file-store", "data"),
    prevent_initial_call=True,
)
def process_uploaded_data(file_path: Path | str | None) -> tuple[str | None, str | None]:
    """Process the uploaded pickle file and store the processed data.

    Args:
        file_path: Path to the uploaded pickle file.

    Returns:
        JSON string of processed data or None if processing fails.
    """
    if file_path is None:
        return None, None

    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        # Extract and process the necessary data
        bgcs, gcfs, _, _, _, links = data

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

        if links is not None:
            processed_links: dict[str, Any] = {
                "gcf_id": [],
                "spectrum_id": [],
                "strains": [],
                "method": [],
                "score": [],
                "cutoff": [],
                "standardised": [],
            }

            for link in links.links:
                for method, data in link[2].items():
                    processed_links["gcf_id"].append(link[0].id)
                    processed_links["spectrum_id"].append(link[1].id)
                    processed_links["strains"].append([s.id for s in link[1].strains._strains])
                    processed_links["method"].append(method)
                    processed_links["score"].append(data.value)
                    processed_links["cutoff"].append(data.parameter["cutoff"])
                    processed_links["standardised"].append(data.parameter["standardised"])
        else:
            processed_links = {}

        return json.dumps(processed_data), json.dumps(processed_links)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None, None


@app.callback(
    [
        Output("gm-tab", "disabled"),
        Output("gm-filter-accordion-control", "disabled"),
        Output("gm-filter-blocks-id", "data", allow_duplicate=True),
        Output("gm-filter-blocks-container", "children", allow_duplicate=True),
        Output("gm-table-card-header", "style"),
        Output("gm-table-card-body", "style", allow_duplicate=True),
        Output("gm-scoring-accordion-control", "disabled"),
        Output("gm-scoring-blocks-id", "data", allow_duplicate=True),
        Output("gm-scoring-blocks-container", "children", allow_duplicate=True),
        Output("gm-results-button", "disabled"),
        Output("mg-tab", "disabled"),
    ],
    [Input("file-store", "data")],
    prevent_initial_call=True,
)
def disable_tabs_and_reset_blocks(
    file_path: Path | str | None,
) -> tuple[
    bool,
    bool,
    list[str],
    list[dmc.Grid],
    dict,
    dict[str, str],
    bool,
    list[str],
    list[dmc.Grid],
    bool,
    bool,
]:
    """Manage tab states and reset blocks based on file upload status.

    Args:
        file_path: The name of the uploaded file, or None if no file is uploaded.

    Returns:
        Tuple containing boolean values for disabling tabs, styles, and new block data.
    """
    if file_path is None:
        # Disable the tabs, don't change blocks
        return True, True, [], [], {}, {"display": "block"}, True, [], [], True, True

    # Enable the tabs and reset blocks
    gm_filter_initial_block_id = [str(uuid.uuid4())]
    gm_filter_new_blocks = [gm_filter_create_initial_block(gm_filter_initial_block_id[0])]
    gm_scoring_initial_block_id = [str(uuid.uuid4())]
    gm_scoring_new_blocks = [gm_scoring_create_initial_block(gm_scoring_initial_block_id[0])]

    return (
        False,
        False,
        gm_filter_initial_block_id,
        gm_filter_new_blocks,
        {},
        {"display": "block"},
        False,
        gm_scoring_initial_block_id,
        gm_scoring_new_blocks,
        False,
        False,
    )


@app.callback(
    Output("gm-graph", "figure"),
    Output("gm-graph", "style"),
    Output("mg-file-content", "children"),
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


# Filter callbacks
def gm_filter_create_initial_block(block_id: str) -> dmc.Grid:
    """Create the initial block component with the given ID.

    Args:
        block_id: A unique identifier for the block.

    Returns:
        A Grid component with nested elements.
    """
    return dmc.Grid(
        id={"type": "gm-filter-block", "index": block_id},
        children=[
            dmc.GridCol(
                dbc.Button(
                    [html.I(className="fas fa-plus")],
                    id={"type": "gm-filter-add-button", "index": block_id},
                    className="btn-primary",
                ),
                span=2,
            ),
            dmc.GridCol(
                dcc.Dropdown(
                    options=GM_FILTER_DROPDOWN_MENU_OPTIONS,
                    value="GCF_ID",
                    id={"type": "gm-filter-dropdown-menu", "index": block_id},
                    clearable=False,
                ),
                span=4,
            ),
            dmc.GridCol(
                [
                    dmc.TextInput(
                        id={"type": "gm-filter-dropdown-ids-text-input", "index": block_id},
                        placeholder="1, 2, 3, ...",
                        className="custom-textinput",
                    ),
                    dcc.Dropdown(
                        id={"type": "gm-filter-dropdown-bgc-class-dropdown", "index": block_id},
                        options=GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS,
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
    Output("gm-filter-blocks-id", "data"),
    Input({"type": "gm-filter-add-button", "index": ALL}, "n_clicks"),
    State("gm-filter-blocks-id", "data"),
)
def gm_filter_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
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
    Output("gm-filter-blocks-container", "children"),
    Input("gm-filter-blocks-id", "data"),
    State("gm-filter-blocks-container", "children"),
)
def gm_filter_display_blocks(
    blocks_id: list[str], existing_blocks: list[dmc.Grid]
) -> list[dmc.Grid]:
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
            id={"type": "gm-filter-block", "index": new_block_id},
            children=[
                dmc.GridCol(
                    html.Div(
                        [
                            dbc.Button(
                                [html.I(className="fas fa-plus")],
                                id={"type": "gm-filter-add-button", "index": new_block_id},
                                className="btn-primary",
                            ),
                            html.Label(
                                "OR",
                                id={"type": "gm-filter-or-label", "index": new_block_id},
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
                        options=GM_FILTER_DROPDOWN_MENU_OPTIONS,
                        value="GCF_ID",
                        id={"type": "gm-filter-dropdown-menu", "index": new_block_id},
                        clearable=False,
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    [
                        dmc.TextInput(
                            id={"type": "gm-filter-dropdown-ids-text-input", "index": new_block_id},
                            placeholder="1, 2, 3, ...",
                            className="custom-textinput",
                        ),
                        dcc.Dropdown(
                            id={
                                "type": "gm-filter-dropdown-bgc-class-dropdown",
                                "index": new_block_id,
                            },
                            options=GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS,
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
    Output({"type": "gm-filter-dropdown-ids-text-input", "index": MATCH}, "style"),
    Output({"type": "gm-filter-dropdown-bgc-class-dropdown", "index": MATCH}, "style"),
    Output({"type": "gm-filter-dropdown-ids-text-input", "index": MATCH}, "placeholder"),
    Output({"type": "gm-filter-dropdown-bgc-class-dropdown", "index": MATCH}, "placeholder"),
    Output({"type": "gm-filter-dropdown-ids-text-input", "index": MATCH}, "value"),
    Output({"type": "gm-filter-dropdown-bgc-class-dropdown", "index": MATCH}, "value"),
    Input({"type": "gm-filter-dropdown-menu", "index": MATCH}, "value"),
)
def gm_filter_update_placeholder(
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


# First table callbacks
def gm_filter_apply(
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
    Output("gm-table-select-all-checkbox", "value"),
    Input("processed-data-store", "data"),
    Input("gm-filter-apply-button", "n_clicks"),
    State({"type": "gm-filter-dropdown-menu", "index": ALL}, "value"),
    State({"type": "gm-filter-dropdown-ids-text-input", "index": ALL}, "value"),
    State({"type": "gm-filter-dropdown-bgc-class-dropdown", "index": ALL}, "value"),
    State("gm-table-select-all-checkbox", "value"),
    prevent_initial_call=True,
)
def gm_table_update_datatable(
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

    if ctx.triggered_id == "gm-filter-apply-button":
        # Apply filters only when the button is clicked
        filtered_df = gm_filter_apply(df, dropdown_menus, text_inputs, bgc_class_dropdowns)
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
    Input("gm-table-select-all-checkbox", "value"),
    State("gm-table", "data"),
    State("gm-table", "derived_virtual_data"),
    prevent_initial_call=True,
)
def gm_table_toggle_selection(
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
def gm_table_select_rows(
    rows: list[dict[str, Any]], selected_rows: list[int] | None
) -> tuple[str, str]:
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

    # TODO: to be removed later when the scoring part will be implemented
    output1 = f"Total rows: {len(df)}"
    output2 = f"Selected rows: {len(selected_rows)}\nSelected GCF IDs: {', '.join(selected_rows_data['GCF ID'].astype(str))}"

    return output1, output2


# Scoring filter callbacks
def gm_scoring_create_initial_block(block_id: str) -> dmc.Grid:
    """Create the initial block component with the given ID.

    Args:
        block_id: A unique identifier for the block.

    Returns:
        A Grid component with nested elements.
    """
    return dmc.Grid(
        id={"type": "gm-scoring-block", "index": block_id},
        children=[
            dmc.GridCol(span=6),
            dmc.GridCol(
                dcc.RadioItems(
                    ["RAW", "STANDARDISED"],
                    "RAW",
                    inline=True,
                    id={"type": "gm-scoring-radio-items", "index": block_id},
                    labelStyle={
                        "marginRight": "20px",
                        "padding": "8px 12px",
                        "backgroundColor": "#f0f0f0",
                        "border": "1px solid #ddd",
                        "borderRadius": "4px",
                        "cursor": "pointer",
                    },
                ),
                span=6,
            ),
            dmc.GridCol(
                dbc.Button(
                    [html.I(className="fas fa-plus")],
                    id={"type": "gm-scoring-add-button", "index": block_id},
                    className="btn-primary",
                    style={"marginTop": "24px"},
                ),
                span=2,
            ),
            dmc.GridCol(
                dcc.Dropdown(
                    options=GM_SCORING_DROPDOWN_MENU_OPTIONS,
                    value="METCALF",
                    id={"type": "gm-scoring-dropdown-menu", "index": block_id},
                    clearable=False,
                    style={"marginTop": "24px"},
                ),
                span=4,
            ),
            dmc.GridCol(
                [
                    dmc.TextInput(
                        id={"type": "gm-scoring-dropdown-ids-cutoff-met", "index": block_id},
                        label="Cutoff",
                        placeholder="Insert cutoff value as a number",
                        value="0.05",
                        className="custom-textinput",
                    )
                ],
                span=6,
            ),
        ],
        gutter="md",
    )


@app.callback(
    Output("gm-scoring-blocks-id", "data"),
    Input({"type": "gm-scoring-add-button", "index": ALL}, "n_clicks"),
    State("gm-scoring-blocks-id", "data"),
)
def gm_scoring_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
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
    Output("gm-scoring-blocks-container", "children"),
    Input("gm-scoring-blocks-id", "data"),
    State("gm-scoring-blocks-container", "children"),
)
def gm_scoring_display_blocks(
    blocks_id: list[str], existing_blocks: list[dmc.Grid]
) -> list[dmc.Grid]:
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
            id={"type": "gm-scoring-block", "index": new_block_id},
            children=[
                dmc.GridCol(span=6),
                dmc.GridCol(
                    dcc.RadioItems(
                        ["RAW", "STANDARDISED"],
                        "RAW",
                        inline=True,
                        id={"type": "gm-scoring-radio-items", "index": new_block_id},
                        labelStyle={
                            "marginRight": "20px",
                            "padding": "8px 12px",
                            "backgroundColor": "#f0f0f0",
                            "border": "1px solid #ddd",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                        },
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    html.Div(
                        [
                            dbc.Button(
                                [html.I(className="fas fa-plus")],
                                id={"type": "gm-scoring-add-button", "index": new_block_id},
                                className="btn-primary",
                            ),
                            html.Label(
                                "OR",
                                id={"type": "gm-scoring-or-label", "index": new_block_id},
                                className="ms-2 px-2 py-1 rounded",
                                style={
                                    "color": "green",
                                    "backgroundColor": "#f0f0f0",
                                    "display": "inline-block",
                                    "position": "absolute",
                                    "left": "50px",
                                },
                            ),
                        ],
                    ),
                    style={"position": "relative", "marginTop": "24px"},
                    span=2,
                ),
                dmc.GridCol(
                    dcc.Dropdown(
                        options=GM_SCORING_DROPDOWN_MENU_OPTIONS,
                        value="METCALF",
                        id={"type": "gm-scoring-dropdown-menu", "index": new_block_id},
                        clearable=False,
                        style={"marginTop": "24px"},
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    [
                        dmc.TextInput(
                            id={
                                "type": "gm-scoring-dropdown-ids-cutoff-met",
                                "index": new_block_id,
                            },
                            label="Cutoff",
                            placeholder="Insert cutoff value as a number",
                            value="0.05",
                            className="custom-textinput",
                        ),
                    ],
                    span=6,
                ),
            ],
            gutter="md",
            style={"marginTop": "30px"},
        )

        # Hide the add button and OR label on the previous last block
        if len(existing_blocks) == 1:
            existing_blocks[-1]["props"]["children"][2]["props"]["children"]["props"]["style"] = {
                "display": "none"
            }
        else:
            existing_blocks[-1]["props"]["children"][2]["props"]["children"]["props"]["children"][
                0
            ]["props"]["style"] = {"display": "none"}

        return existing_blocks + [new_block]
    return existing_blocks


@app.callback(
    Output({"type": "gm-scoring-radio-items", "index": MATCH}, "style"),
    Output({"type": "gm-scoring-dropdown-ids-cutoff-met", "index": MATCH}, "label"),
    Output({"type": "gm-scoring-dropdown-ids-cutoff-met", "index": MATCH}, "value"),
    Input({"type": "gm-scoring-dropdown-menu", "index": MATCH}, "value"),
)
def gm_scoring_update_placeholder(
    selected_value: str,
) -> tuple[dict[str, str], str, str]:
    """Update the style and label of the radio items and input fields based on the dropdown selection.

    Args:
        selected_value: The value selected in the dropdown menu.

    Returns:
        A tuple containing st syle and label updates of the radio items and input fields.
    """
    if not ctx.triggered:
        # Callback was not triggered by user interaction, don't change anything
        raise dash.exceptions.PreventUpdate
    if selected_value == "METCALF":
        return ({"display": "block"}, "Cutoff", "0.05")
    else:
        # This case should never occur due to the Literal type, but it satisfies mypy
        return ({"display": "none"}, "", "")


# Results table callbacks
def gm_scoring_apply(
    df: pd.DataFrame, dropdown_menus: list[str], radiobuttons: list[str], cutoffs_met: list[str]
) -> pd.DataFrame:
    """Apply scoring filters to the DataFrame based on user inputs.

    Args:
        df: The input DataFrame.
        dropdown_menus: List of selected dropdown menu options.
        radiobuttons: List of selected radio button options.
        cutoffs_met: List of cutoff values for METCALF method.

    Returns:
        Filtered DataFrame.
    """
    for menu, radiobutton, cutoff_met in zip(dropdown_menus, radiobuttons, cutoffs_met):
        if menu == "METCALF":
            masked_df = df[df["method"] == "metcalf"]
            if radiobutton == "RAW":
                masked_df = masked_df[~masked_df["standardised"]]
            else:
                masked_df = masked_df[masked_df["standardised"]]

            if cutoff_met:
                masked_df = masked_df[masked_df["cutoff"] >= float(cutoff_met)]

        return masked_df
    else:
        return df


# TODO: Add tests
@app.callback(
    Output("gm-results-alert", "children"),
    Output("gm-results-alert", "is_open"),
    Output("gm-results-table", "data"),
    Output("gm-results-table", "columns"),
    Output("gm-results-table-card-body", "style"),
    Input("gm-results-button", "n_clicks"),
    Input("gm-table", "derived_virtual_data"),
    Input("gm-table", "derived_virtual_selected_rows"),
    State("processed-links-store", "data"),
    State({"type": "gm-scoring-dropdown-menu", "index": ALL}, "value"),
    State({"type": "gm-scoring-radio-items", "index": ALL}, "value"),
    State({"type": "gm-scoring-dropdown-ids-cutoff-met", "index": ALL}, "value"),
)
def gm_update_results_datatable(
    n_clicks: int | None,
    virtual_data: list[dict] | None,
    selected_rows: list[int] | None,
    processed_links: str,
    dropdown_menus: list[str],
    radiobuttons: list[str],
    cutoffs_met: list[str],
) -> tuple[str, bool, list[dict], list[dict], dict]:
    """Update the results DataTable based on scoring filters.

    Args:
        n_clicks: Number of times the "Show Results" button has been clicked.
        virtual_data: Current filtered data from the GCF table.
        selected_rows: Indices of selected rows in the GCF table.
        processed_links: JSON string of processed links data.
        dropdown_menus: List of selected dropdown menu options.
        radiobuttons: List of selected radio button options.
        cutoffs_met: List of cutoff values for METCALF method.

    Returns:
        Tuple containing alert message, visibility state, table data and settings.
    """
    triggered_id = ctx.triggered_id

    if triggered_id in ["gm-table-select-all-checkbox", "gm-table"]:
        return "", False, [], [], {"display": "none"}

    if n_clicks is None:
        return "", False, [], [], {"display": "none"}

    if not selected_rows:
        return (
            "No GCFs selected. Please select GCFs and try again.",
            True,
            [],
            [],
            {"display": "none"},
        )

    if not virtual_data:
        return "No data available.", True, [], [], {"display": "none"}

    try:
        links_data = json.loads(processed_links)
        if len(links_data) == 0:
            return "No processed links available.", True, [], [], {"display": "none"}

        # Get selected GCF IDs
        selected_gcfs = [virtual_data[i]["GCF ID"] for i in selected_rows]

        # Convert links data to DataFrame
        links_df = pd.DataFrame(links_data)

        # Apply scoring filters
        filtered_df = gm_scoring_apply(links_df, dropdown_menus, radiobuttons, cutoffs_met)

        # Filter for selected GCFs and aggregate results
        results = []
        for gcf_id in selected_gcfs:
            gcf_links = filtered_df[filtered_df["gcf_id"] == gcf_id]
            if not gcf_links.empty:
                results.append(
                    {
                        "GCF ID": gcf_id,
                        "# Links": len(gcf_links),
                        "Average Score": round(gcf_links["score"].mean(), 2),
                    }
                )

        if not results:
            return "No matching links found for selected GCFs.", True, [], [], {"display": "none"}

        columns = [
            {"name": "GCF ID", "id": "GCF ID"},
            {"name": "# Links", "id": "# Links", "type": "numeric"},
            {"name": "Average Score", "id": "Average Score", "type": "numeric"},
        ]

        return "", False, results, columns, {"display": "block"}

    except Exception as e:
        return f"Error processing results: {str(e)}", True, [], [], {"display": "none"}
