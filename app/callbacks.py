import io
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
from config import GM_RESULTS_TABLE_MANDATORY_COLUMNS
from config import GM_RESULTS_TABLE_OPTIONAL_COLUMNS
from config import MG_FILTER_DROPDOWN_MENU_OPTIONS
from config import MG_RESULTS_TABLE_MANDATORY_COLUMNS
from config import MG_RESULTS_TABLE_OPTIONAL_COLUMNS
from config import SCORING_DROPDOWN_MENU_OPTIONS
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
from nplinker.metabolomics.molecular_family import MolecularFamily
from nplinker.metabolomics.spectrum import Spectrum


# TODO: Add new tests for the mg table
# TODO: Add underlines to the rows with tooltips in the tables


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


# ------------------ Upload and Process Data ------------------ #
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
        _, gcfs, _, mfs, _, links = data

        def process_bgc_class(bgc_class: tuple[str, ...] | None) -> list[str]:
            if bgc_class is None:
                return ["Unknown"]
            return list(bgc_class)  # Convert tuple to list

        processed_data: dict[str, Any] = {"n_bgcs": {}, "gcf_data": [], "mf_data": []}

        for gcf in gcfs:
            sorted_bgcs = sorted(gcf.bgcs, key=lambda bgc: bgc.id)
            bgc_ids = [bgc.id for bgc in sorted_bgcs]
            bgc_classes = [process_bgc_class(bgc.mibig_bgc_class) for bgc in sorted_bgcs]

            processed_data["gcf_data"].append(
                {
                    "GCF ID": gcf.id,
                    "# BGCs": len(gcf.bgcs),
                    "BGC IDs": bgc_ids,
                    "BGC Classes": bgc_classes,
                    "strains": sorted([s.id for s in gcf.strains._strains]),
                }
            )

            if len(gcf.bgcs) not in processed_data["n_bgcs"]:
                processed_data["n_bgcs"][len(gcf.bgcs)] = []
            processed_data["n_bgcs"][len(gcf.bgcs)].append(gcf.id)

        for mf in mfs:
            sorted_spectra = sorted(mf.spectra, key=lambda spectrum: spectrum.id)
            processed_data["mf_data"].append(
                {
                    "MF ID": mf.id,
                    "# Spectra": len(mf.spectra_ids),
                    "Spectra IDs": list(spectrum.id for spectrum in sorted_spectra),
                    "Spectra precursor m/z": [spectrum.precursor_mz for spectrum in sorted_spectra],
                    "Spectra GNPS IDs": [spectrum.gnps_id for spectrum in sorted_spectra],
                    "strains": sorted([s.id for s in mf.strains._strains]),
                }
            )

        if links is not None:
            processed_links: dict[str, Any] = {
                "gm_data": {
                    "gcf_id": [],
                    "spectrum": [],
                    "method": [],
                    "score": [],
                    "cutoff": [],
                    "standardised": [],
                },
                "mg_data": {
                    "mf_id": [],
                    "gcf": [],
                    "method": [],
                    "score": [],
                    "cutoff": [],
                    "standardised": [],
                },
            }

            for link in links.links:
                if isinstance(link[1], Spectrum):  # Then link[0] is a GCF (GCF -> Spectrum)
                    processed_links["gm_data"]["gcf_id"].append(link[0].id)
                    processed_links["gm_data"]["spectrum"].append(
                        {
                            "id": link[1].id,
                            "strains": sorted([s.id for s in link[1].strains._strains]),
                            "precursor_mz": link[1].precursor_mz,
                            "gnps_id": link[1].gnps_id,
                        }
                    )
                    for method, data in link[2].items():
                        processed_links["gm_data"]["method"].append(method)
                        processed_links["gm_data"]["score"].append(data.value)
                        processed_links["gm_data"]["cutoff"].append(data.parameter["cutoff"])
                        processed_links["gm_data"]["standardised"].append(
                            data.parameter["standardised"]
                        )
                elif isinstance(link[1], MolecularFamily):  # Then link[0] if GCFS (GCF -> MF)
                    sorted_bgcs = sorted(link[0].bgcs, key=lambda bgc: bgc.id)
                    bgc_ids = [bgc.id for bgc in sorted_bgcs]
                    bgc_classes = [process_bgc_class(bgc.mibig_bgc_class) for bgc in sorted_bgcs]

                    processed_links["mg_data"]["mf_id"].append(link[1].id)
                    processed_links["mg_data"]["gcf"].append(
                        {
                            "id": link[0].id,
                            "strains": sorted([s.id for s in link[1].strains._strains]),
                            "# BGCs": len(link[0].bgcs),
                            "BGC IDs": bgc_ids,
                            "BGC Classes": bgc_classes,
                        }
                    )
                    for method, data in link[2].items():
                        processed_links["mg_data"]["method"].append(method)
                        processed_links["mg_data"]["score"].append(data.value)
                        processed_links["mg_data"]["cutoff"].append(data.parameter["cutoff"])
                        processed_links["mg_data"]["standardised"].append(
                            data.parameter["standardised"]
                        )
        else:
            processed_links = {}

        return json.dumps(processed_data), json.dumps(processed_links)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None, None


@app.callback(
    [
        # GM tab outputs
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
        # MG tab outputs
        Output("mg-tab", "disabled"),
        Output("mg-filter-accordion-control", "disabled"),
        Output("mg-filter-blocks-id", "data", allow_duplicate=True),
        Output("mg-filter-blocks-container", "children", allow_duplicate=True),
        Output("mg-table-card-header", "style"),
        Output("mg-table-card-body", "style", allow_duplicate=True),
        Output("mg-scoring-accordion-control", "disabled"),
        Output("mg-scoring-blocks-id", "data", allow_duplicate=True),
        Output("mg-scoring-blocks-container", "children", allow_duplicate=True),
        Output("mg-results-button", "disabled"),
    ],
    [Input("file-store", "data")],
    prevent_initial_call=True,
)
def disable_tabs_and_reset_blocks(
    file_path: Path | str | None,
) -> tuple:
    """Manage tab states and reset blocks based on file upload status for both GM and MG tabs.

    Args:
        file_path: The name of the uploaded file, or None if no file is uploaded.

    Returns:
        Tuple containing boolean values for disabling tabs, styles, and new block data.
    """
    if file_path is None:
        # Disable all tabs and controls when no file is uploaded
        return (
            # GM tab - disabled
            True,
            True,
            [],
            [],
            {},
            {"display": "block"},
            True,
            [],
            [],
            True,
            # MG tab - disabled
            True,
            True,
            [],
            [],
            {},
            {"display": "block"},
            True,
            [],
            [],
            True,
        )

    # Enable the tabs and reset blocks
    # GM tab initial blocks
    gm_filter_initial_block_id = [str(uuid.uuid4())]
    gm_filter_new_blocks = [gm_filter_create_initial_block(gm_filter_initial_block_id[0])]
    gm_scoring_initial_block_id = [str(uuid.uuid4())]
    gm_scoring_new_blocks = [scoring_create_initial_block(gm_scoring_initial_block_id[0], "gm")]

    # MG tab initial blocks
    mg_filter_initial_block_id = [str(uuid.uuid4())]
    mg_filter_new_blocks = [mg_filter_create_initial_block(mg_filter_initial_block_id[0])]
    mg_scoring_initial_block_id = [str(uuid.uuid4())]
    mg_scoring_new_blocks = [scoring_create_initial_block(mg_scoring_initial_block_id[0], "mg")]

    return (
        # GM tab - enabled with initial blocks
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
        # MG tab - enabled with initial blocks
        False,
        False,
        mg_filter_initial_block_id,
        mg_filter_new_blocks,
        {},
        {"display": "block"},
        False,
        mg_scoring_initial_block_id,
        mg_scoring_new_blocks,
        False,
    )


# ------------------ GM Plot ------------------ #
@app.callback(
    Output("gm-graph", "figure"),
    Output("gm-graph", "style"),
    [Input("processed-data-store", "data")],
)
def gm_plot(stored_data: str | None) -> tuple[dict | go.Figure, dict]:
    """Create a bar plot based on the processed data.

    Args:
        stored_data: JSON string of processed data or None.

    Returns:
        Tuple containing the plot figure, style, and a status message.
    """
    if stored_data is None:
        return {}, {"display": "none"}
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
    return fig, {"display": "block"}


# ------------------ Common Filter and Table Functions ------------------ #
def filter_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
    """Add a new block to the layout when the add button is clicked.

    Generic function to handle both GM and MG filter block additions.

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


def table_toggle_selection(
    value: list | None,
    original_rows: list,
    filtered_rows: list | None,
) -> list:
    """Toggle between selecting all rows and deselecting all rows in the current view of a Dash DataTable.

    Generic function to handle both GM and MG table row selections.

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


# ------------------ GM Filter functions ------------------ #
def gm_filter_create_initial_block(block_id: str) -> dmc.Grid:
    """Create the initial block component for the GM tab with the given ID.

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
    """Add a new block to the GM filters layout when the add button is clicked.

    Calls the common filter_add_block function.

    Args:
        n_clicks: List of number of clicks for each add button.
        blocks_id: Current list of block IDs.

    Returns:
        Updated list of block IDs.
    """
    return filter_add_block(n_clicks, blocks_id)


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


# ------------------ MG Filter functions ------------------ #
def mg_filter_create_initial_block(block_id: str) -> dmc.Grid:
    """Create the initial filter block component for the MG tab with the given ID.

    Args:
        block_id: A unique identifier for the block.

    Returns:
        A Grid component with nested elements.
    """
    return dmc.Grid(
        id={"type": "mg-filter-block", "index": block_id},
        children=[
            dmc.GridCol(
                dbc.Button(
                    [html.I(className="fas fa-plus")],
                    id={"type": "mg-filter-add-button", "index": block_id},
                    className="btn-primary",
                ),
                span=2,
            ),
            dmc.GridCol(
                dcc.Dropdown(
                    options=MG_FILTER_DROPDOWN_MENU_OPTIONS,
                    value="MF_ID",
                    id={"type": "mg-filter-dropdown-menu", "index": block_id},
                    clearable=False,
                ),
                span=4,
            ),
            dmc.GridCol(
                [
                    dmc.TextInput(
                        id={"type": "mg-filter-dropdown-mf-ids-text-input", "index": block_id},
                        placeholder="1, 2, 3, ...",
                        className="custom-textinput",
                    ),
                    dmc.TextInput(
                        id={"type": "mg-filter-dropdown-spec-ids-text-input", "index": block_id},
                        placeholder="1, 2, 3, ...",
                        className="custom-textinput",
                        style={"display": "none"},
                    ),
                ],
                span=6,
            ),
        ],
        gutter="md",
    )


@app.callback(
    Output("mg-filter-blocks-id", "data"),
    Input({"type": "mg-filter-add-button", "index": ALL}, "n_clicks"),
    State("mg-filter-blocks-id", "data"),
)
def mg_filter_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
    """Add a new block to the MG filters layout when the add button is clicked.

    Calls the common filter_add_block function.

    Args:
        n_clicks: List of number of clicks for each add button.
        blocks_id: Current list of block IDs.

    Returns:
        Updated list of block IDs.
    """
    return filter_add_block(n_clicks, blocks_id)


@app.callback(
    Output("mg-filter-blocks-container", "children"),
    Input("mg-filter-blocks-id", "data"),
    State("mg-filter-blocks-container", "children"),
)
def mg_filter_display_blocks(
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
            id={"type": "mg-filter-block", "index": new_block_id},
            children=[
                dmc.GridCol(
                    html.Div(
                        [
                            dbc.Button(
                                [html.I(className="fas fa-plus")],
                                id={"type": "mg-filter-add-button", "index": new_block_id},
                                className="btn-primary",
                            ),
                            html.Label(
                                "OR",
                                id={"type": "mg-filter-or-label", "index": new_block_id},
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
                        options=MG_FILTER_DROPDOWN_MENU_OPTIONS,
                        value="MF_ID",
                        id={"type": "mg-filter-dropdown-menu", "index": new_block_id},
                        clearable=False,
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    [
                        dmc.TextInput(
                            id={
                                "type": "mg-filter-dropdown-mf-ids-text-input",
                                "index": new_block_id,
                            },
                            placeholder="1, 2, 3, ...",
                            className="custom-textinput",
                        ),
                        dmc.TextInput(
                            id={
                                "type": "mg-filter-dropdown-spec-ids-text-input",
                                "index": new_block_id,
                            },
                            placeholder="1, 2, 3, ...",
                            className="custom-textinput",
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
    Output({"type": "mg-filter-dropdown-mf-ids-text-input", "index": MATCH}, "style"),
    Output({"type": "mg-filter-dropdown-spec-ids-text-input", "index": MATCH}, "style"),
    Output({"type": "mg-filter-dropdown-mf-ids-text-input", "index": MATCH}, "placeholder"),
    Output({"type": "mg-filter-dropdown-spec-ids-text-input", "index": MATCH}, "placeholder"),
    Output({"type": "mg-filter-dropdown-mf-ids-text-input", "index": MATCH}, "value"),
    Output({"type": "mg-filter-dropdown-spec-ids-text-input", "index": MATCH}, "value"),
    Input({"type": "mg-filter-dropdown-menu", "index": MATCH}, "value"),
)
def mg_filter_update_placeholder(
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
    if selected_value == "MF_ID":
        return {"display": "block"}, {"display": "none"}, "1, 2, 3, ...", "", "", []
    elif selected_value == "SPECTRUM_ID":
        return (
            {"display": "none"},
            {"display": "block"},
            "",
            "1, 2, 3, ...",
            "",
            [],
        )
    else:
        # This case should never occur due to the Literal type, but it satisfies mypy
        return {"display": "none"}, {"display": "none"}, "", "", "", []


# ------------------ GM Data Table functions ------------------ #
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
            # Get unique classes for filtering
            mask = df["BGC Classes"].apply(
                lambda x: any(
                    bc.lower() in {item.lower() for sublist in x for item in sublist}
                    for bc in bgc_classes
                )
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

    # Prepare tooltip data
    tooltip_data = []
    for _, row in filtered_df.iterrows():
        bgc_tooltip_markdown = "| BGC ID | Class |\n|---------|--------|\n" + "\n".join(
            [
                f"| {bgc_id} | {', '.join(bgc_class)} |"
                for bgc_id, bgc_class in zip(row["BGC IDs"], row["BGC Classes"])
            ]
        )
        strains_markdown = "| Strains |\n|----------|\n" + "\n".join(
            [f"| {strain} |" for strain in row["strains"]]
        )

        tooltip_data.append(
            {
                "# BGCs": {"value": bgc_tooltip_markdown, "type": "markdown"},
                "GCF ID": {"value": strains_markdown, "type": "markdown"},
            }
        )

    # Prepare the data for display
    filtered_df["BGC IDs"] = filtered_df["BGC IDs"].apply(lambda x: ", ".join(map(str, x)))
    filtered_df["BGC Classes"] = filtered_df["BGC Classes"].apply(
        lambda x: ", ".join({item for sublist in x for item in sublist})  # Unique flattened classes
    )
    filtered_df["MiBIG IDs"] = filtered_df["strains"].apply(
        lambda x: ", ".join([s for s in x if s.startswith("BGC")]) or "None"
    )
    filtered_df["strains"] = filtered_df["strains"].apply(", ".join)

    columns = [
        {"name": "GCF ID", "id": "GCF ID"},
        {"name": "# BGCs", "id": "# BGCs", "type": "numeric"},
        {"name": "BGC Classes", "id": "BGC Classes"},
        {"name": "MiBIG IDs", "id": "MiBIG IDs"},
    ]

    return (
        filtered_df.to_dict("records"),
        columns,
        tooltip_data,
        {"display": "block"},
        [],
        new_checkbox_value,
    )


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
    """Toggle between selecting all rows and deselecting all rows in the GM DataTable.

    Calls the common table_toggle_selection function.

    Args:
        value: Value of the select-all checkbox.
        original_rows: All rows in the table.
        filtered_rows: Rows visible after filtering, or None if no filter is applied.

    Returns:
        List of indices of selected rows after toggling.
    """
    return table_toggle_selection(value, original_rows, filtered_rows)


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

    output1 = f"Total rows: {len(df)}"
    output2 = f"Selected rows: {len(selected_rows)}\nSelected GCF IDs: {', '.join(selected_rows_data['GCF ID'].astype(str))}"

    return output1, output2


# ------------------ MG Data Table functions ------------------ #


def mg_filter_apply(
    df: pd.DataFrame,
    dropdown_menus: list[str],
    mf_text_inputs: list[str],
    spec_text_inputs: list[str],
) -> pd.DataFrame:
    """Apply filters to the DataFrame based on user inputs.

    Args:
        df: The input DataFrame.
        dropdown_menus: List of selected dropdown menu options.
        mf_text_inputs: List of text inputs for MF IDs.
        spec_text_inputs: List of text inputs for Spectrum IDs.

    Returns:
        Filtered DataFrame.
    """
    masks = []

    for menu, mf_text_input, spec_text_input in zip(
        dropdown_menus, mf_text_inputs, spec_text_inputs
    ):
        if menu == "MF_ID" and mf_text_input:
            mf_ids = [id.strip() for id in mf_text_input.split(",") if id.strip()]
            if mf_ids:
                mask = df["MF ID"].astype(str).isin(mf_ids)
                masks.append(mask)
        elif menu == "SPECTRUM_ID" and spec_text_input:
            spectrum_ids = [id.strip() for id in spec_text_input.split(",") if id.strip()]
            if spectrum_ids:
                # Convert to set of strings for efficient lookup
                spectrum_ids_set = set(spectrum_ids)
                # Check if any of the spectrum IDs exactly match any ID in the Spectra IDs list
                mask = df["Spectra IDs"].apply(lambda x: any(str(s) in spectrum_ids_set for s in x))
                masks.append(mask)

    if masks:
        # Combine all masks with OR operation
        final_mask = pd.concat(masks, axis=1).any(axis=1)
        return df[final_mask]
    else:
        return df


@app.callback(
    Output("mg-table", "data"),
    Output("mg-table", "columns"),
    Output("mg-table", "tooltip_data"),
    Output("mg-table-card-body", "style"),
    Output("mg-table", "selected_rows", allow_duplicate=True),
    Output("mg-table-select-all-checkbox", "value"),
    Input("processed-data-store", "data"),
    Input("mg-filter-apply-button", "n_clicks"),
    State({"type": "mg-filter-dropdown-menu", "index": ALL}, "value"),
    State({"type": "mg-filter-dropdown-mf-ids-text-input", "index": ALL}, "value"),
    State({"type": "mg-filter-dropdown-spec-ids-text-input", "index": ALL}, "value"),
    State("mg-table-select-all-checkbox", "value"),
    prevent_initial_call=True,
)
def mg_table_update_datatable(
    processed_data: str | None,
    n_clicks: int | None,
    dropdown_menus: list[str],
    mf_text_inputs: list[str],
    spec_text_inputs: list[str],
    checkbox_value: list | None,
) -> tuple[list[dict], list[dict], list[dict], dict, list, list]:
    """Update the DataTable based on processed data and applied filters when the button is clicked.

    Args:
        processed_data: JSON string of processed data.
        n_clicks: Number of times the Apply Filters button has been clicked.
        dropdown_menus: List of selected dropdown menu options.
        mf_text_inputs: List of text inputs for MF IDs.
        spec_text_inputs: List of text inputs for Spectrum IDs.
        checkbox_value: Current value of the select-all checkbox.

    Returns:
        Tuple containing table data, column definitions, tooltips data, style, empty selected rows, and updated checkbox value.
    """
    if processed_data is None:
        return [], [], [], {"display": "none"}, [], []

    try:
        data = json.loads(processed_data)
        df = pd.DataFrame(data["mf_data"])
    except (json.JSONDecodeError, KeyError, pd.errors.EmptyDataError):
        return [], [], [], {"display": "none"}, [], []

    if ctx.triggered_id == "mg-filter-apply-button":
        # Apply filters only when the button is clicked
        filtered_df = mg_filter_apply(df, dropdown_menus, mf_text_inputs, spec_text_inputs)
        # Reset the checkbox when filters are applied
        new_checkbox_value = []
    else:
        # On initial load or when processed data changes, show all data
        filtered_df = df
        new_checkbox_value = checkbox_value if checkbox_value is not None else []

    # Prepare tooltip data
    tooltip_data = []
    for _, row in filtered_df.iterrows():
        # Limit spectra entries in tooltip with 'more entries' indicator
        max_tooltip_entries = 10
        spectra_count = len(row["Spectra IDs"])

        # Create spectra tooltip without GNPS ID column
        spectra_tooltip_markdown = "| Spectrum ID | Precursor m/z |\n|------------|-------------|\n"

        # Add top entries limited to max_tooltip_entries
        for i in range(min(max_tooltip_entries, spectra_count)):
            spec_id = row["Spectra IDs"][i]
            precursor_mz = row["Spectra precursor m/z"][i]
            spectra_tooltip_markdown += f"| {spec_id} | {precursor_mz:.4f} |\n"

        # Add indication of more entries if applicable
        if spectra_count > max_tooltip_entries:
            remaining = spectra_count - max_tooltip_entries
            spectra_tooltip_markdown += f"\n... {remaining} more entries ..."

        # Limit strains entries in tooltip with 'more entries' indicator
        strains = row["strains"]
        strains_count = len(strains)
        max_strains_entries = 10

        strains_markdown = "| Strains |\n|----------|\n"
        # Add top entries limited to max_strains_entries
        for i in range(min(max_strains_entries, strains_count)):
            strains_markdown += f"| {strains[i]} |\n"

        # Add indication of more entries if applicable
        if strains_count > max_strains_entries:
            remaining = strains_count - max_strains_entries
            strains_markdown += f"\n... {remaining} more entries ..."

        tooltip_data.append(
            {
                "# Spectra": {"value": spectra_tooltip_markdown, "type": "markdown"},
                "MF ID": {"value": strains_markdown, "type": "markdown"},
            }
        )

    # Prepare the data for display
    filtered_df["Spectra GNPS IDs"] = filtered_df["Spectra GNPS IDs"].apply(
        lambda x: ", ".join({str(gnps_id) for gnps_id in x if gnps_id}) if x else "None"
    )
    filtered_df["Display Spectra GNPS IDs"] = filtered_df["Spectra GNPS IDs"].apply(
        lambda x: ", ".join({str(gnps_id) for gnps_id in x if gnps_id and str(gnps_id) != "None"})
        or "None"
    )

    filtered_df["Spectra IDs"] = filtered_df["Spectra IDs"].apply(lambda x: ", ".join(map(str, x)))

    # Calculate average precursor m/z and display
    filtered_df["Spectra precursor m/z"] = filtered_df["Spectra precursor m/z"].apply(
        lambda x: ", ".join([str(round(val, 4)) for val in x]) if x else "N/A"
    )
    filtered_df["strains"] = filtered_df["strains"].apply(", ".join)

    columns = [
        {"name": "MF ID", "id": "MF ID"},
        {"name": "# Spectra", "id": "# Spectra", "type": "numeric"},
        {"name": "Spectra GNPS IDs", "id": "Display Spectra GNPS IDs"},
    ]

    return (
        filtered_df.to_dict("records"),
        columns,
        tooltip_data,
        {"display": "block"},
        [],
        new_checkbox_value,
    )


@app.callback(
    Output("mg-table", "selected_rows", allow_duplicate=True),
    Input("mg-table-select-all-checkbox", "value"),
    State("mg-table", "data"),
    State("mg-table", "derived_virtual_data"),
    prevent_initial_call=True,
)
def mg_table_toggle_selection(
    value: list | None,
    original_rows: list,
    filtered_rows: list | None,
) -> list:
    """Toggle between selecting all rows and deselecting all rows in the MG DataTable.

    Calls the common table_toggle_selection function.

    Args:
        value: Value of the select-all checkbox.
        original_rows: All rows in the table.
        filtered_rows: Rows visible after filtering, or None if no filter is applied.

    Returns:
        List of indices of selected rows after toggling.
    """
    return table_toggle_selection(value, original_rows, filtered_rows)


@app.callback(
    Output("mg-table-output1", "children"),
    Output("mg-table-output2", "children"),
    Input("mg-table", "derived_virtual_data"),
    Input("mg-table", "derived_virtual_selected_rows"),
)
def mg_table_select_rows(
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

    output1 = f"Total rows: {len(df)}"
    output2 = f"Selected rows: {len(selected_rows)}\nSelected MF IDs: {', '.join(selected_rows_data['MF ID'].astype(str))}"

    return output1, output2


# ------------------ Common Scoring functions ------------------ #
def scoring_create_initial_block(block_id: str, tab_prefix: str = "gm") -> dmc.Grid:
    """Create the initial scoring block component for either GM or MG tab with the given ID.

    Args:
        block_id: A unique identifier for the block.
        tab_prefix: Prefix for the tab ('gm' or 'mg') to determine which dropdown options to use.

    Returns:
        A Grid component with nested elements.
    """
    return dmc.Grid(
        id={"type": f"{tab_prefix}-scoring-block", "index": block_id},
        children=[
            dmc.GridCol(span=6),
            dmc.GridCol(
                dcc.RadioItems(
                    ["RAW", "STANDARDISED"],
                    "RAW",
                    inline=True,
                    id={"type": f"{tab_prefix}-scoring-radio-items", "index": block_id},
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
                    id={"type": f"{tab_prefix}-scoring-add-button", "index": block_id},
                    className="btn-primary",
                    style={"marginTop": "24px"},
                ),
                span=2,
            ),
            dmc.GridCol(
                dcc.Dropdown(
                    options=SCORING_DROPDOWN_MENU_OPTIONS,
                    value="METCALF",
                    id={"type": f"{tab_prefix}-scoring-dropdown-menu", "index": block_id},
                    clearable=False,
                    style={"marginTop": "24px"},
                ),
                span=4,
            ),
            dmc.GridCol(
                [
                    dmc.TextInput(
                        id={
                            "type": f"{tab_prefix}-scoring-dropdown-ids-cutoff-met",
                            "index": block_id,
                        },
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


def scoring_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
    """Add a new block to the scoring layout when the add button is clicked.

    Generic function to handle both GM and MG scoring block additions.

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


def scoring_display_blocks(
    blocks_id: list[str], existing_blocks: list[dmc.Grid], tab_prefix: str = "gm"
) -> list[dmc.Grid]:
    """Display the scoring blocks for the input block IDs.

    Generic function to handle both GM and MG scoring block displays.

    Args:
        blocks_id: List of block IDs.
        existing_blocks: Current list of block components.
        tab_prefix: Prefix for the tab ('gm' or 'mg').

    Returns:
        Updated list of block components.
    """
    if len(blocks_id) > 1:
        new_block_id = blocks_id[-1]

        new_block = dmc.Grid(
            id={"type": f"{tab_prefix}-scoring-block", "index": new_block_id},
            children=[
                dmc.GridCol(span=6),
                dmc.GridCol(
                    dcc.RadioItems(
                        ["RAW", "STANDARDISED"],
                        "RAW",
                        inline=True,
                        id={"type": f"{tab_prefix}-scoring-radio-items", "index": new_block_id},
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
                                id={
                                    "type": f"{tab_prefix}-scoring-add-button",
                                    "index": new_block_id,
                                },
                                className="btn-primary",
                            ),
                            html.Label(
                                "OR",
                                id={
                                    "type": f"{tab_prefix}-scoring-or-label",
                                    "index": new_block_id,
                                },
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
                        options=SCORING_DROPDOWN_MENU_OPTIONS,
                        value="METCALF",
                        id={"type": f"{tab_prefix}-scoring-dropdown-menu", "index": new_block_id},
                        clearable=False,
                        style={"marginTop": "24px"},
                    ),
                    span=4,
                ),
                dmc.GridCol(
                    [
                        dmc.TextInput(
                            id={
                                "type": f"{tab_prefix}-scoring-dropdown-ids-cutoff-met",
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


def scoring_update_placeholder(
    selected_value: str,
) -> tuple[dict[str, str], str, str]:
    """Update the style and label of the radio items and input fields based on the dropdown selection.

    Generic function to handle both GM and MG scoring placeholders.

    Args:
        selected_value: The value selected in the dropdown menu.

    Returns:
        A tuple containing style and label updates of the radio items and input fields.
    """
    if not ctx.triggered:
        # Callback was not triggered by user interaction, don't change anything
        raise dash.exceptions.PreventUpdate
    if selected_value == "METCALF":
        return ({"display": "block"}, "Cutoff", "0.05")
    else:
        # This case should never occur due to the Literal type, but it satisfies mypy
        return ({"display": "none"}, "", "")


def scoring_apply(
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


# ------------------ GM Scoring functions ------------------ #
@app.callback(
    Output("gm-scoring-blocks-id", "data"),
    Input({"type": "gm-scoring-add-button", "index": ALL}, "n_clicks"),
    State("gm-scoring-blocks-id", "data"),
)
def gm_scoring_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
    """Add a new block to the GM scoring layout when the add button is clicked.

    Args:
        n_clicks: List of number of clicks for each add button.
        blocks_id: Current list of block IDs.

    Returns:
        Updated list of block IDs.
    """
    return scoring_add_block(n_clicks, blocks_id)


@app.callback(
    Output("gm-scoring-blocks-container", "children"),
    Input("gm-scoring-blocks-id", "data"),
    State("gm-scoring-blocks-container", "children"),
)
def gm_scoring_display_blocks(
    blocks_id: list[str], existing_blocks: list[dmc.Grid]
) -> list[dmc.Grid]:
    """Display the blocks for the input block IDs in the GM tab.

    Args:
        blocks_id: List of block IDs.
        existing_blocks: Current list of block components.

    Returns:
        Updated list of block components.
    """
    return scoring_display_blocks(blocks_id, existing_blocks, "gm")


@app.callback(
    Output({"type": "gm-scoring-radio-items", "index": MATCH}, "style"),
    Output({"type": "gm-scoring-dropdown-ids-cutoff-met", "index": MATCH}, "label"),
    Output({"type": "gm-scoring-dropdown-ids-cutoff-met", "index": MATCH}, "value"),
    Input({"type": "gm-scoring-dropdown-menu", "index": MATCH}, "value"),
)
def gm_scoring_update_placeholder(
    selected_value: str,
) -> tuple[dict[str, str], str, str]:
    """Update the style and label of the radio items and input fields for GM tab.

    Args:
        selected_value: The value selected in the dropdown menu.

    Returns:
        A tuple containing style and label updates of the radio items and input fields.
    """
    return scoring_update_placeholder(selected_value)


# ------------------ MG Scoring functions ------------------ #


@app.callback(
    Output("mg-scoring-blocks-id", "data"),
    Input({"type": "mg-scoring-add-button", "index": ALL}, "n_clicks"),
    State("mg-scoring-blocks-id", "data"),
)
def mg_scoring_add_block(n_clicks: list[int], blocks_id: list[str]) -> list[str]:
    """Add a new block to the MG scoring layout when the add button is clicked.

    Args:
        n_clicks: List of number of clicks for each add button.
        blocks_id: Current list of block IDs.

    Returns:
        Updated list of block IDs.
    """
    return scoring_add_block(n_clicks, blocks_id)


@app.callback(
    Output("mg-scoring-blocks-container", "children"),
    Input("mg-scoring-blocks-id", "data"),
    State("mg-scoring-blocks-container", "children"),
)
def mg_scoring_display_blocks(
    blocks_id: list[str], existing_blocks: list[dmc.Grid]
) -> list[dmc.Grid]:
    """Display the blocks for the input block IDs in the MG tab.

    Args:
        blocks_id: List of block IDs.
        existing_blocks: Current list of block components.

    Returns:
        Updated list of block components.
    """
    return scoring_display_blocks(blocks_id, existing_blocks, "mg")


@app.callback(
    Output({"type": "mg-scoring-radio-items", "index": MATCH}, "style"),
    Output({"type": "mg-scoring-dropdown-ids-cutoff-met", "index": MATCH}, "label"),
    Output({"type": "mg-scoring-dropdown-ids-cutoff-met", "index": MATCH}, "value"),
    Input({"type": "mg-scoring-dropdown-menu", "index": MATCH}, "value"),
)
def mg_scoring_update_placeholder(
    selected_value: str,
) -> tuple[dict[str, str], str, str]:
    """Update the style and label of the radio items and input fields for MG tab.

    Args:
        selected_value: The value selected in the dropdown menu.

    Returns:
        A tuple containing style and label updates of the radio items and input fields.
    """
    return scoring_update_placeholder(selected_value)


# ------------------ GM Results table functions ------------------ #


@app.callback(
    Output("gm-results-table-column-settings-modal", "is_open"),
    [
        Input("gm-results-table-column-settings-button", "n_clicks"),
        Input("gm-results-table-column-settings-close", "n_clicks"),
    ],
    [State("gm-results-table-column-settings-modal", "is_open")],
)
def toggle_column_settings_modal(n1, n2, is_open):
    """Toggle the visibility of the column settings modal.

    Args:
        n1: Number of clicks on the open button.
        n2: Number of clicks on the close button.
        is_open: Current state of the modal (open or closed).

    Returns:
        The new state of the modal (open or closed).
    """
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("gm-results-table", "columns"),
    [
        Input("gm-results-table-column-toggle", "value"),
        Input("gm-results-button", "n_clicks"),
    ],
)
def update_columns(selected_columns: list[str] | None, n_clicks: int | None) -> list[dict]:
    """Update the columns of the results table based on user selections.

    Args:
        selected_columns: List of selected columns to display.
        n_clicks: Number of times the "Show Results" button has been clicked.

    Returns:
        List of column definitions for the results table.
    """
    # Start with mandatory columns
    columns: list[dict] = GM_RESULTS_TABLE_MANDATORY_COLUMNS.copy()

    # Create a dictionary for optional columns lookup
    optional_columns_dict = {col["id"]: col for col in GM_RESULTS_TABLE_OPTIONAL_COLUMNS}

    # Add the selected columns in the order they appear in selected_columns
    if selected_columns:
        columns.extend(
            [
                optional_columns_dict[col_id]
                for col_id in selected_columns
                if col_id in optional_columns_dict
            ]
        )

    return columns


@app.callback(
    Output("gm-results-alert", "children"),
    Output("gm-results-alert", "is_open"),
    Output("gm-results-table", "data"),
    Output("gm-results-table", "tooltip_data"),
    Output("gm-results-table-card-body", "style"),
    Output("gm-results-table-card-header", "style"),
    Output("gm-results-table-column-settings-button", "disabled"),
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
) -> tuple[str, bool, list[dict], list[dict], dict, dict, bool]:
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
        Tuple containing alert message, visibility state, table data and settings, and header style.
    """
    triggered_id = ctx.triggered_id

    if triggered_id in ["gm-table-select-all-checkbox", "gm-table"]:
        return "", False, [], [], {"display": "none"}, {"color": "#888888"}, True

    if n_clicks is None:
        return "", False, [], [], {"display": "none"}, {"color": "#888888"}, True

    if not selected_rows:
        return (
            "No GCFs selected. Please select GCFs and try again.",
            True,
            [],
            [],
            {"display": "none"},
            {"color": "#888888"},
            True,
        )

    if not virtual_data:
        return "No data available.", True, [], [], {"display": "none"}, {"color": "#888888"}, True

    try:
        links_data = json.loads(processed_links)
        if len(links_data) == 0:
            return (
                "No processed links available.",
                True,
                [],
                [],
                {"display": "none"},
                {"color": "#888888"},
                True,
            )

        links_data = links_data["gm_data"]
        # Get selected GCF IDs and their corresponding data
        selected_gcfs = {
            row["GCF ID"]: {
                "MiBIG IDs": row["MiBIG IDs"],
                "BGC Classes": row["BGC Classes"],
            }
            for i, row in enumerate(virtual_data)
            if i in selected_rows
        }

        # Convert links data to DataFrame
        links_df = pd.DataFrame(links_data)

        # Apply scoring filters
        filtered_df = scoring_apply(links_df, dropdown_menus, radiobuttons, cutoffs_met)

        # Filter for selected GCFs and aggregate results
        results = []
        for gcf_id in selected_gcfs:
            gcf_links = filtered_df[filtered_df["gcf_id"] == gcf_id]
            if not gcf_links.empty:
                # Sort by score in descending order
                gcf_links = gcf_links.sort_values("score", ascending=False)

                top_spectrum = gcf_links.iloc[0]
                result = {
                    # Mandatory fields
                    "GCF ID": int(gcf_id),
                    "# Links": len(gcf_links),
                    "Average Score": round(gcf_links["score"].mean(), 2),
                    # Optional fields with None handling
                    "Top Spectrum ID": int(top_spectrum["spectrum"].get("id", float("nan"))),
                    "Top Spectrum Precursor m/z": round(
                        top_spectrum["spectrum"].get("precursor_mz", float("nan")), 4
                    )
                    if top_spectrum["spectrum"].get("precursor_mz") is not None
                    else float("nan"),
                    "Top Spectrum GNPS ID": top_spectrum["spectrum"].get("gnps_id", "None")
                    if top_spectrum["spectrum"].get("gnps_id") is not None
                    else "None",
                    "Top Spectrum Score": round(top_spectrum.get("score", float("nan")), 4)
                    if top_spectrum.get("score") is not None
                    else float("nan"),
                    "MiBIG IDs": selected_gcfs[gcf_id]["MiBIG IDs"],
                    "BGC Classes": selected_gcfs[gcf_id]["BGC Classes"],
                    # Store all spectrum data for later use (download, etc.)
                    "spectrum_ids_str": "|".join(
                        [str(s.get("id", "")) for s in gcf_links["spectrum"]]
                    ),
                    "spectrum_scores_str": "|".join(
                        [str(score) for score in gcf_links["score"].tolist()]
                    ),
                }
                results.append(result)

        if not results:
            return (
                "No matching links found for selected GCFs.",
                True,
                [],
                [],
                {"display": "none"},
                {"color": "#888888"},
                True,
            )

        # Prepare tooltip data
        tooltip_data = []
        for result in results:
            spectrum_ids = (
                result["spectrum_ids_str"].split("|") if result["spectrum_ids_str"] else []
            )
            spectrum_scores = (
                [float(s) for s in result["spectrum_scores_str"].split("|")]
                if result["spectrum_scores_str"]
                else []
            )
            # Show only top 5 spectrums in tooltip
            max_tooltip_entries = 5
            total_entries = len(result["spectrum_ids_str"])

            spectrums_table = "| Spectrum ID | Score |\n|------------|--------|\n"

            # Add top entries
            for spectrum_id, score in zip(
                spectrum_ids[:max_tooltip_entries],
                spectrum_scores[:max_tooltip_entries],
            ):
                spectrums_table += f"| {spectrum_id} | {round(score, 4)} |\n"

            # Add indication of more entries if applicable
            if total_entries > max_tooltip_entries:
                remaining = total_entries - max_tooltip_entries
                spectrums_table += f"\n... {remaining} more entries ..."

            row_tooltip = {
                "# Links": {"value": spectrums_table, "type": "markdown"},
            }
            tooltip_data.append(row_tooltip)

        return (
            "",
            False,
            results,
            tooltip_data,
            {"display": "block"},
            {},
            False,
        )

    except Exception as e:
        return (
            f"Error processing results: {str(e)}",
            True,
            [],
            [],
            {"display": "none"},
            {"color": "#888888"},
            True,
        )


@app.callback(
    [
        Output("gm-download-button", "disabled"),
        Output("gm-download-alert", "is_open"),
        Output("gm-download-alert", "children"),
    ],
    [
        Input("gm-results-table", "data"),
    ],
)
def toggle_download_button(table_data):
    """Enable/disable download button based on data availability."""
    if not table_data:
        return True, False, ""
    return False, False, ""


@app.callback(
    [
        Output("gm-download-excel", "data"),
        Output("gm-download-alert", "is_open", allow_duplicate=True),
        Output("gm-download-alert", "children", allow_duplicate=True),
    ],
    Input("gm-download-button", "n_clicks"),
    [
        State("gm-results-table", "data"),
    ],
    prevent_initial_call=True,
)
def generate_excel(n_clicks, table_data):
    """Generate Excel file with two sheets: full results and detailed spectrum data."""
    if not ctx.triggered or not table_data:
        return None, False, ""

    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Sheet 1: Best candidate links table
            results_df = pd.DataFrame(table_data)

            # Filter out only the internal fields used for tooltips and processing
            internal_fields = ["spectrum_ids_str", "spectrum_scores_str"]
            export_columns = [col for col in results_df.columns if col not in internal_fields]

            # Use all non-internal columns
            results_df = results_df[export_columns]
            results_df.to_excel(writer, sheet_name="Best Candidate Links", index=False)

            # Sheet 2: Detailed spectrum data
            detailed_data = []
            for row in table_data:
                gcf_id = row["GCF ID"]
                spectrum_ids = (
                    row.get("spectrum_ids_str", "").split("|")
                    if row.get("spectrum_ids_str")
                    else []
                )
                scores = (
                    [float(s) for s in row.get("spectrum_scores_str", "").split("|")]
                    if row.get("spectrum_scores_str")
                    else []
                )

                # Add all spectrum entries without truncation
                for spectrum_id, score in zip(spectrum_ids, scores):
                    detailed_data.append(
                        {"GCF ID": gcf_id, "Spectrum ID": int(spectrum_id), "Score": score}
                    )

            detailed_df = pd.DataFrame(detailed_data)
            detailed_df.to_excel(writer, sheet_name="All Candidate Links", index=False)

        # Prepare the file for download
        excel_data = output.getvalue()
        return dcc.send_bytes(excel_data, "nplinker_genom_to_metabol.xlsx"), False, ""
    except Exception as e:
        return None, True, f"Error generating Excel file: {str(e)}"


# ------------------ MG Results table functions ------------------ #


@app.callback(
    Output("mg-results-table-column-settings-modal", "is_open"),
    [
        Input("mg-results-table-column-settings-button", "n_clicks"),
        Input("mg-results-table-column-settings-close", "n_clicks"),
    ],
    [State("mg-results-table-column-settings-modal", "is_open")],
)
def toggle_mg_column_settings_modal(n1, n2, is_open):
    """Toggle the visibility of the column settings modal.

    Args:
        n1: Number of clicks on the open button.
        n2: Number of clicks on the close button.
        is_open: Current state of the modal (open or closed).

    Returns:
        The new state of the modal (open or closed).
    """
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("mg-results-table", "columns"),
    [
        Input("mg-results-table-column-toggle", "value"),
        Input("mg-results-button", "n_clicks"),
    ],
)
def update_mg_columns(selected_columns: list[str] | None, n_clicks: int | None) -> list[dict]:
    """Update the columns of the results table based on user selections.

    Args:
        selected_columns: List of selected columns to display.
        n_clicks: Number of times the "Show Results" button has been clicked.

    Returns:
        List of column definitions for the results table.
    """
    # Start with mandatory columns
    columns: list[dict] = MG_RESULTS_TABLE_MANDATORY_COLUMNS.copy()

    # Create a dictionary for optional columns lookup
    optional_columns_dict = {col["id"]: col for col in MG_RESULTS_TABLE_OPTIONAL_COLUMNS}

    # Add the selected columns in the order they appear in selected_columns
    if selected_columns:
        columns.extend(
            [
                optional_columns_dict[col_id]
                for col_id in selected_columns
                if col_id in optional_columns_dict
            ]
        )

    return columns


@app.callback(
    Output("mg-results-alert", "children"),
    Output("mg-results-alert", "is_open"),
    Output("mg-results-table", "data"),
    Output("mg-results-table", "tooltip_data"),
    Output("mg-results-table-card-body", "style"),
    Output("mg-results-table-card-header", "style"),
    Output("mg-results-table-column-settings-button", "disabled"),
    Input("mg-results-button", "n_clicks"),
    Input("mg-table", "derived_virtual_data"),
    Input("mg-table", "derived_virtual_selected_rows"),
    State("processed-links-store", "data"),
    State({"type": "mg-scoring-dropdown-menu", "index": ALL}, "value"),
    State({"type": "mg-scoring-radio-items", "index": ALL}, "value"),
    State({"type": "mg-scoring-dropdown-ids-cutoff-met", "index": ALL}, "value"),
)
def mg_update_results_datatable(
    n_clicks: int | None,
    virtual_data: list[dict] | None,
    selected_rows: list[int] | None,
    processed_links: str,
    dropdown_menus: list[str],
    radiobuttons: list[str],
    cutoffs_met: list[str],
) -> tuple[str, bool, list[dict], list[dict], dict, dict, bool]:
    """Update the results DataTable based on scoring filters.

    Args:
        n_clicks: Number of times the "Show Results" button has been clicked.
        virtual_data: Current filtered data from the MF table.
        selected_rows: Indices of selected rows in the MF table.
        processed_links: JSON string of processed links data.
        dropdown_menus: List of selected dropdown menu options.
        radiobuttons: List of selected radio button options.
        cutoffs_met: List of cutoff values for METCALF method.

    Returns:
        Tuple containing alert message, visibility state, table data and settings, and header style.
    """
    triggered_id = ctx.triggered_id

    if triggered_id in ["mg-table-select-all-checkbox", "mg-table"]:
        return "", False, [], [], {"display": "none"}, {"color": "#888888"}, True

    if n_clicks is None:
        return "", False, [], [], {"display": "none"}, {"color": "#888888"}, True

    if not selected_rows:
        return (
            "No MFs selected. Please select MFs and try again.",
            True,
            [],
            [],
            {"display": "none"},
            {"color": "#888888"},
            True,
        )

    if not virtual_data:
        return "No data available.", True, [], [], {"display": "none"}, {"color": "#888888"}, True

    try:
        links_data = json.loads(processed_links)
        if len(links_data) == 0:
            return (
                "No processed links available.",
                True,
                [],
                [],
                {"display": "none"},
                {"color": "#888888"},
                True,
            )

        links_data = links_data["mg_data"]
        # Get selected MF IDs and spectrum IDs
        selected_mfs = {
            row["MF ID"]: {
                "Spectra IDs": row["Spectra IDs"].split(", ")
                if isinstance(row["Spectra IDs"], str)
                else [],
                "Spectra GNPS IDs": row["Spectra GNPS IDs"].split(", ")
                if isinstance(row["Spectra GNPS IDs"], str)
                else [],
                "Spectra precursor m/z": row["Spectra precursor m/z"].split(", ")
                if isinstance(row["Spectra precursor m/z"], str)
                else [],
            }
            for i, row in enumerate(virtual_data)
            if i in selected_rows
        }

        # Convert links data to DataFrame
        links_df = pd.DataFrame(links_data)

        # Apply scoring filters
        filtered_df = scoring_apply(links_df, dropdown_menus, radiobuttons, cutoffs_met)
        # Filter for selected MFs and aggregate results
        results = []
        for mf_id in selected_mfs:
            mf_links = filtered_df[filtered_df["mf_id"] == mf_id]
            if not mf_links.empty:
                # Sort by score in descending order
                mf_links = mf_links.sort_values("score", ascending=False)

                # Get the top GCF for this MF
                top_gcf = mf_links.iloc[0]

                result = {
                    # Mandatory fields
                    "MF ID": int(mf_id),
                    "# Links": len(mf_links),
                    "Average Score": round(mf_links["score"].mean(), 2),
                    # # Optional fields
                    "Top GCF ID": int(top_gcf["gcf"].get("id", float("nan"))),
                    "Top GCF # BGCs": top_gcf["gcf"].get("# BGCs", 0),
                    "Top GCF BGC IDs": ", ".join([str(s) for s in top_gcf["gcf"]["BGC IDs"]]),
                    "Top GCF BGC Classes": ", ".join(
                        {
                            item
                            for sublist in top_gcf["gcf"].get("BGC Classes", [])
                            for item in sublist
                        }
                    ),
                    "Top GCF Score": round(top_gcf.get("score", float("nan")), 4),
                    # Store all GCF data for later use (download, etc.)
                    "gcf_ids_str": "|".join([str(gcf.get("id", "")) for gcf in mf_links["gcf"]]),
                    "gcf_scores_str": "|".join(
                        [str(score) for score in mf_links["score"].tolist()]
                    ),
                }
                results.append(result)

        if not results:
            return (
                "No matching links found for selected MFs.",
                True,
                [],
                [],
                {"display": "none"},
                {"color": "#888888"},
                True,
            )

        # Prepare tooltip data
        tooltip_data = []
        for result in results:
            gcf_ids = result["gcf_ids_str"].split("|") if result["gcf_ids_str"] else []
            gcf_scores = (
                [float(s) for s in result["gcf_scores_str"].split("|")]
                if result["gcf_scores_str"]
                else []
            )

            # Show only top 5 GCFs in tooltip
            max_tooltip_entries = 5
            total_entries = len(gcf_ids)

            gcfs_table = "| GCF ID | Score |\n|--------|--------|\n"

            # Add top entries
            for gcf_id, score in zip(
                gcf_ids[:max_tooltip_entries],
                gcf_scores[:max_tooltip_entries],
            ):
                gcfs_table += f"| {gcf_id} | {round(score, 4)} |\n"

            # Add indication of more entries if applicable
            if total_entries > max_tooltip_entries:
                remaining = total_entries - max_tooltip_entries
                gcfs_table += f"\n... {remaining} more entries ..."

            row_tooltip = {
                "# Links": {"value": gcfs_table, "type": "markdown"},
            }
            tooltip_data.append(row_tooltip)

        return (
            "",
            False,
            results,
            tooltip_data,
            {"display": "block"},
            {},
            False,
        )

    except Exception as e:
        return (
            f"Error processing results: {str(e)}",
            True,
            [],
            [],
            {"display": "none"},
            {"color": "#888888"},
            True,
        )


@app.callback(
    [
        Output("mg-download-button", "disabled"),
        Output("mg-download-alert", "is_open"),
        Output("mg-download-alert", "children"),
    ],
    [
        Input("mg-results-table", "data"),
    ],
)
def toggle_mg_download_button(table_data):
    """Enable/disable download button based on data availability."""
    if not table_data:
        return True, False, ""
    return False, False, ""


@app.callback(
    [
        Output("mg-download-excel", "data"),
        Output("mg-download-alert", "is_open", allow_duplicate=True),
        Output("mg-download-alert", "children", allow_duplicate=True),
    ],
    Input("mg-download-button", "n_clicks"),
    [
        State("mg-results-table", "data"),
    ],
    prevent_initial_call=True,
)
def generate_mg_excel(n_clicks, table_data):
    """Generate Excel file with two sheets: full results and detailed GCF data."""
    if not ctx.triggered or not table_data:
        return None, False, ""

    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Sheet 1: Best candidate links table
            results_df = pd.DataFrame(table_data)

            # Filter out only the internal fields used for tooltips and processing
            internal_fields = ["gcf_ids_str", "gcf_scores_str"]
            export_columns = [col for col in results_df.columns if col not in internal_fields]

            # Use all non-internal columns
            results_df = results_df[export_columns]
            results_df.to_excel(writer, sheet_name="Best Candidate Links", index=False)

            # Sheet 2: Detailed GCF data
            detailed_data = []
            for row in table_data:
                mf_id = row["MF ID"]
                gcf_ids = row.get("gcf_ids_str", "").split("|") if row.get("gcf_ids_str") else []
                scores = (
                    [float(s) for s in row.get("gcf_scores_str", "").split("|")]
                    if row.get("gcf_scores_str")
                    else []
                )

                # Add all GCF entries without truncation
                for gcf_id, score in zip(gcf_ids, scores):
                    detailed_data.append(
                        {
                            "MF ID": mf_id,
                            "GCF ID": int(gcf_id),
                            "Score": score,
                        }
                    )

            detailed_df = pd.DataFrame(detailed_data)
            detailed_df.to_excel(writer, sheet_name="All Candidate Links", index=False)

        # Prepare the file for download
        excel_data = output.getvalue()
        return dcc.send_bytes(excel_data, "nplinker_metabol_to_genom.xlsx"), False, ""
    except Exception as e:
        return None, True, f"Error generating Excel file: {str(e)}"
