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
import requests
from config import GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_PRE_V4
from config import GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_V4
from config import GM_FILTER_DROPDOWN_MENU_OPTIONS
from config import GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from config import GM_RESULTS_TABLE_MANDATORY_COLUMNS
from config import GM_RESULTS_TABLE_OPTIONAL_COLUMNS
from config import MAX_TOOLTIP_ROWS
from config import MG_FILTER_DROPDOWN_MENU_OPTIONS
from config import MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
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
from dash import dcc
from dash import html
from app.config import GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_PRE_V4
from app.config import GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_V4
from app.config import GM_FILTER_DROPDOWN_MENU_OPTIONS
from app.config import GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from app.config import GM_RESULTS_TABLE_MANDATORY_COLUMNS
from app.config import GM_RESULTS_TABLE_OPTIONAL_COLUMNS
from app.config import MAX_TOOLTIP_ROWS
from app.config import MG_FILTER_DROPDOWN_MENU_OPTIONS
from app.config import MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from app.config import MG_RESULTS_TABLE_MANDATORY_COLUMNS
from app.config import MG_RESULTS_TABLE_OPTIONAL_COLUMNS
from app.config import SCORING_DROPDOWN_MENU_OPTIONS
from nplinker.metabolomics.molecular_family import MolecularFamily
from nplinker.metabolomics.spectrum import Spectrum


dash._dash_renderer._set_react_version("18.2.0")  # type: ignore


dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED, dbc_css, dbc.icons.FONT_AWESOME])
# Configure the upload folder
TEMP_DIR = tempfile.mkdtemp()
du.configure_upload(app, TEMP_DIR)

DEMO_DATA_URL = (
    "https://github.com/NPLinker/nplinker-webapp/blob/main/tests/data/mock_obj_data.pkl?raw=true"
)


# ------------------ Upload and Process Data ------------------ #
@du.callback(
    id="dash-uploader",
    output=[
        Output("dash-uploader-output", "children"),
        Output("file-store", "data"),
        Output("loading-spinner-container", "children", allow_duplicate=True),
    ],
)
def upload_data(status: du.UploadStatus) -> tuple[str, str | None, None]:
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
                None,
            )
        except (pickle.UnpicklingError, EOFError, AttributeError):
            return f"Error: {os.path.basename(latest_file)} is not a valid pickle file.", None, None
        except Exception as e:
            # Handle any other unexpected errors
            return f"Error uploading file: {str(e)}", None, None
    return "No file uploaded", None, None


@app.callback(
    Output("dash-uploader-output", "children", allow_duplicate=True),
    Output("file-store", "data", allow_duplicate=True),
    Output("loading-spinner-container", "children", allow_duplicate=True),
    Input("demo-data-button", "n_clicks"),
    prevent_initial_call=True,
)
def load_demo_data(n_clicks):
    """Load demo data from GitHub repository.

    Args:
        n_clicks: Number of times the demo data button has been clicked.

    Returns:
        A tuple containing a message string and the file path (if successful).
    """
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    try:
        # Download the demo data
        response = requests.get(DEMO_DATA_URL, timeout=30)
        response.raise_for_status()

        # Save to temporary file
        demo_file_path = os.path.join(TEMP_DIR, f"demo_data_{uuid.uuid4()}.pkl")
        with open(demo_file_path, "wb") as f:
            f.write(response.content)

        # Validate the pickle file
        with open(demo_file_path, "rb") as f:
            pickle.load(f)

        file_size_mb = len(response.content) / (1024 * 1024)

        return (
            f"Successfully loaded demo data: demo_data.pkl [{round(file_size_mb, 2)} MB]",
            str(demo_file_path),
            None,
        )

    except requests.exceptions.RequestException as e:
        return f"Error downloading demo data: Network error - {str(e)}", None, None
    except (pickle.UnpicklingError, EOFError, AttributeError):
        return "Error: Downloaded file is not a valid pickle file.", None, None
    except Exception as e:
        return f"Error loading demo data: {str(e)}", None, None


@app.callback(
    Output("processed-data-store", "data"),
    Output("processed-links-store", "data"),
    Output("loading-spinner-container", "children", allow_duplicate=True),
    Input("file-store", "data"),
    prevent_initial_call=True,
)
def process_uploaded_data(
    file_path: Path | str | None, cleanup: bool = True
) -> tuple[str | None, str | None, str | None]:
    """Process the uploaded pickle file and store the processed data.

    Args:
        file_path: Path to the uploaded pickle file.
        cleanup: Flag to indicate whether to clean up the file after processing.

    Returns:
        JSON string of processed data or None if processing fails.
    """
    if file_path is None:
        return None, None, None

    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        # Extract and process the necessary data
        _, gcfs, _, mfs, _, links = data

        def process_bgc_class(bgc_class: tuple[str, ...] | None) -> list[str]:
            if bgc_class is None:
                return ["Unknown"]
            return list(bgc_class)  # Convert tuple to list

        processed_data: dict[str, Any] = {
            "gcf_data": [],
            "n_bgcs": {},
            "class_bgcs": {},
            "mf_data": [],
        }

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

            for bgc_class_list in bgc_classes:
                for bgc_class in bgc_class_list:
                    if bgc_class not in processed_data["class_bgcs"]:
                        processed_data["class_bgcs"][bgc_class] = []
                    processed_data["class_bgcs"][bgc_class].append(gcf.id)

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
                # Helper function to process Genome-Metabolome (GM) links
                def process_gm_link(gcf, spectrum, methods_data):
                    processed_links["gm_data"]["gcf_id"].append(gcf.id)
                    processed_links["gm_data"]["spectrum"].append(
                        {
                            "id": spectrum.id,
                            "strains": sorted([s.id for s in spectrum.strains._strains]),
                            "precursor_mz": spectrum.precursor_mz,
                            "gnps_id": spectrum.gnps_id,
                            "mf_id": spectrum.family.id if spectrum.family else None,
                        }
                    )
                    for method, data in methods_data.items():
                        processed_links["gm_data"]["method"].append(method)
                        processed_links["gm_data"]["score"].append(data.value)
                        processed_links["gm_data"]["cutoff"].append(data.parameter["cutoff"])
                        processed_links["gm_data"]["standardised"].append(
                            data.parameter["standardised"]
                        )

                # Helper function to process Metabolome-Genome (MG) links
                def process_mg_link(mf, gcf, methods_data):
                    sorted_bgcs = sorted(gcf.bgcs, key=lambda bgc: bgc.id)
                    bgc_ids = [bgc.id for bgc in sorted_bgcs]
                    bgc_classes = [process_bgc_class(bgc.mibig_bgc_class) for bgc in sorted_bgcs]

                    processed_links["mg_data"]["mf_id"].append(mf.id)
                    processed_links["mg_data"]["gcf"].append(
                        {
                            "id": gcf.id,
                            "strains": sorted([s.id for s in mf.strains._strains]),
                            "# BGCs": len(gcf.bgcs),
                            "BGC IDs": bgc_ids,
                            "BGC Classes": bgc_classes,
                        }
                    )
                    for method, data in methods_data.items():
                        processed_links["mg_data"]["method"].append(method)
                        processed_links["mg_data"]["score"].append(data.value)
                        processed_links["mg_data"]["cutoff"].append(data.parameter["cutoff"])
                        processed_links["mg_data"]["standardised"].append(
                            data.parameter["standardised"]
                        )

                # GCF -> Spectrum links
                if isinstance(link[1], Spectrum):
                    process_gm_link(link[0], link[1], link[2])
                # Spectrum -> GCF links
                elif isinstance(link[0], Spectrum):
                    process_gm_link(link[1], link[0], link[2])
                # GCF -> MF links
                elif isinstance(link[1], MolecularFamily):
                    process_mg_link(link[1], link[0], link[2])
                # MF -> GCF links
                elif isinstance(link[0], MolecularFamily):
                    process_mg_link(link[0], link[1], link[2])
        else:
            processed_links = {}

        return json.dumps(processed_data), json.dumps(processed_links), None
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None, None, None
    finally:
        try:
            if cleanup and file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Cleanup failed for {file_path}: {e}")


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
        Output("gm-table", "selected_rows", allow_duplicate=True),
        Output("gm-table-select-all-checkbox", "value", allow_duplicate=True),
        Output("gm-filter-accordion-component", "value", allow_duplicate=True),
        Output("gm-scoring-accordion-component", "value", allow_duplicate=True),
        Output("gm-results-table-column-toggle", "value", allow_duplicate=True),
        Output("gm-graph-x-axis-selector", "value"),
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
        Output("mg-table", "selected_rows", allow_duplicate=True),
        Output("mg-table-select-all-checkbox", "value", allow_duplicate=True),
        Output("mg-filter-accordion-component", "value", allow_duplicate=True),
        Output("mg-scoring-accordion-component", "value", allow_duplicate=True),
        Output("mg-results-table-column-toggle", "value", allow_duplicate=True),
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
    default_gm_column_value = (
        [GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS[0]]
        if GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
        else []
    )
    default_mg_column_value = (
        [MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS[0]]
        if MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
        else []
    )
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
            [],
            [],
            [],
            [],
            default_gm_column_value,
            "n_bgcs",
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
            [],
            [],
            [],
            [],
            default_mg_column_value,
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
        [],
        [],
        [],
        [],
        default_gm_column_value,
        "n_bgcs",
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
        [],
        [],
        [],
        [],
        default_mg_column_value,
    )


# ------------------ GM Plot ------------------ #
@app.callback(
    Output("gm-graph", "figure"),
    Output("gm-graph", "style"),
    Output("gm-graph-selector-container", "style"),
    [Input("processed-data-store", "data"), Input("gm-graph-x-axis-selector", "value")],
)
def gm_plot(stored_data: str | None, x_axis_selection: str) -> tuple[dict | go.Figure, dict, dict]:
    """Create a bar plot based on the processed data.

    Args:
        stored_data: JSON string of processed data or None.
        x_axis_selection: Selected x-axis type ('n_bgcs' or 'class_bgcs').

    Returns:
        Tuple containing the plot figure, style for graph, and style for selector.
    """
    if stored_data is None:
        return {}, {"display": "none"}, {"display": "none"}

    data = json.loads(stored_data)

    if x_axis_selection == "n_bgcs":
        n_bgcs = data["n_bgcs"]
        x_values = sorted(map(int, n_bgcs.keys()))
        y_values = [len(n_bgcs[str(x)]) for x in x_values]
        hover_texts = [
            f"GCF IDs: {', '.join(str(gcf_id) for gcf_id in n_bgcs[str(x)])}" for x in x_values
        ]

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

    else:  # x_axis_selection == "class_bgcs"
        class_bgcs = data["class_bgcs"]

        # Count unique GCF IDs for each class
        class_gcf_counts = {}
        for bgc_class, gcf_ids in class_bgcs.items():
            # Count unique GCF IDs
            class_gcf_counts[bgc_class] = len(set(gcf_ids))

        # Sort classes by count for better visualization
        sorted_classes = sorted(class_gcf_counts.items(), key=lambda x: x[1], reverse=True)
        x_values = [item[0] for item in sorted_classes]
        y_values = [item[1] for item in sorted_classes]

        # Generate hover texts with line breaks for better readability
        hover_texts = []
        for bgc_class in x_values:
            # Get unique GCF IDs for this class
            unique_gcf_ids = sorted(list(set(class_bgcs[bgc_class])))

            # Format GCF IDs with line breaks every 10 items
            formatted_gcf_ids = ""
            for i, gcf_id in enumerate(unique_gcf_ids):
                formatted_gcf_ids += gcf_id
                # Add comma if not the last item
                if i < len(unique_gcf_ids) - 1:
                    formatted_gcf_ids += ", "
                # Add line break after every 10 items (but not for the last group)
                if (i + 1) % 10 == 0 and i < len(unique_gcf_ids) - 1:
                    formatted_gcf_ids += "<br>"

            hover_text = f"Class: {bgc_class}<br>GCF IDs: {formatted_gcf_ids}"
            hover_texts.append(hover_text)

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
            xaxis_title="BGC Classes",
            yaxis_title="# GCFs",
            xaxis=dict(
                type="category",
                # Add more space for longer class names
                tickangle=-45 if len(x_values) > 5 else 0,
            ),
        )

    return fig, {"display": "block"}, {"display": "block"}


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
                        options=GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_PRE_V4,
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
                            options=GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_PRE_V4,
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
    Output({"type": "gm-filter-dropdown-bgc-class-dropdown", "index": MATCH}, "options"),
    Input({"type": "gm-filter-dropdown-menu", "index": MATCH}, "value"),
    Input("mibig-version-selector", "value"),
    State({"type": "gm-filter-dropdown-bgc-class-dropdown", "index": MATCH}, "value"),
    State({"type": "gm-filter-dropdown-ids-text-input", "index": MATCH}, "value"),
)
def gm_filter_update_placeholder(
    selected_value: str, mibig_version: str, current_bgc_value: list, current_text_value: str
) -> tuple[dict[str, str], dict[str, str], str, str, str, list[Any], list[dict]]:
    """Update the placeholder text, style, and options of input fields based on the dropdown selection and MIBiG version.

    Args:
        selected_value: The value selected in the dropdown menu.
        mibig_version: The selected MIBiG version.
        current_bgc_value: Currently selected BGC class values.
        current_text_value: Currently entered text in the text input.

    Returns:
        A tuple containing style, placeholder, value, and options updates for the input fields.
    """
    # Determine which option set to use based on MIBiG version
    if mibig_version == "v4_plus":
        bgc_options = GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_V4
    else:
        bgc_options = GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_PRE_V4

    # Check what triggered the callback
    triggered_id = ctx.triggered_id

    # If MIBiG version changed, clear the BGC class selection
    if triggered_id == "mibig-version-selector":
        new_bgc_value = []
    else:
        # Otherwise keep the current selection
        new_bgc_value = current_bgc_value

    # Keep the current text input value regardless of what triggered the callback
    text_value = current_text_value if current_text_value else ""

    # Update the styles and placeholders based on the dropdown selection
    if selected_value == "GCF_ID":
        return (
            {"display": "block"},
            {"display": "none"},
            "1, 2, 3, ...",
            "",
            text_value,
            new_bgc_value,
            bgc_options,
        )
    elif selected_value == "BGC_CLASS":
        return (
            {"display": "none"},
            {"display": "block"},
            "",
            "Select one or more BGC classes",
            text_value,
            new_bgc_value,
            bgc_options,
        )
    else:
        # This case should never occur due to the Literal type, but it satisfies mypy
        return (
            {"display": "none"},
            {"display": "none"},
            "",
            "",
            text_value,
            new_bgc_value,
            bgc_options,
        )


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
    Output("loading-spinner-container", "children", allow_duplicate=True),
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
) -> tuple[list[dict], list[dict], list[dict], dict, list, list, str | None]:
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
        return [], [], [], {"display": "none"}, [], [], None

    try:
        data = json.loads(processed_data)
        df = pd.DataFrame(data["gcf_data"])
    except (json.JSONDecodeError, KeyError, pd.errors.EmptyDataError):
        return [], [], [], {"display": "none"}, [], [], None

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
        None,
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

    output1 = f"Total rows: {len(df)}"
    output2 = f"Selected rows: {len(selected_rows)}\n"

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
    Output("loading-spinner-container", "children", allow_duplicate=True),
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
) -> tuple[list[dict], list[dict], list[dict], dict, list, list, str | None]:
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
        return [], [], [], {"display": "none"}, [], [], None

    try:
        data = json.loads(processed_data)
        df = pd.DataFrame(data["mf_data"])
    except (json.JSONDecodeError, KeyError, pd.errors.EmptyDataError):
        return [], [], [], {"display": "none"}, [], [], None

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
        None,
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

    output1 = f"Total rows: {len(df)}"
    output2 = f"Selected rows: {len(selected_rows)}\n"

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
                        label="Scoring method's cutoff (>=)",
                        placeholder="Insert the minimum cutoff value to be considered",
                        value="0",
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
                            label="Scoring method's cutoff (>=)",
                            placeholder="Insert the minimum cutoff value to be considered",
                            value="0",
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
        return ({"display": "block"}, "Cutoff", "0")
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


# ------------------ Common Results Table Functions ------------------
def update_results_datatable(
    n_clicks,
    virtual_data,
    selected_rows,
    processed_links,
    dropdown_menus,
    radiobuttons,
    cutoffs_met,
    prefix,
    item_type,
):
    """Common function for updating results DataTable based on scoring filters.

    Args:
        n_clicks: Number of times the "Show Results" button has been clicked.
        virtual_data: Current filtered data from the table.
        selected_rows: Indices of selected rows in the table.
        processed_links: JSON string of processed links data.
        dropdown_menus: List of selected dropdown menu options.
        radiobuttons: List of selected radio button options.
        cutoffs_met: List of cutoff values for METCALF method.
        prefix: Tab prefix ('gm' or 'mg').
        item_type: Type of item being processed ('GCF' or 'MF').

    Returns:
        Tuple containing alert message, visibility state, table data and settings, header style, and spinner state.
    """
    triggered_id = ctx.triggered_id

    if triggered_id in [f"{prefix}-table-select-all-checkbox", f"{prefix}-table"]:
        return "", False, [], [], {"display": "none"}, {"color": "#888888"}, True, None, {}

    if n_clicks is None:
        return "", False, [], [], {"display": "none"}, {"color": "#888888"}, True, None, {}

    if not selected_rows:
        return (
            f"No {item_type}s selected. Please select {item_type}s and try again.",
            True,
            [],
            [],
            {"display": "none"},
            {"color": "#888888"},
            True,
            None,
            {},
        )

    if not virtual_data:
        return (
            "No data available.",
            True,
            [],
            [],
            {"display": "none"},
            {"color": "#888888"},
            True,
            None,
            {},
        )

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
                None,
                {},
            )

        links_data = links_data[f"{prefix}_data"]

        # Process specific to GM or MG data
        if prefix == "gm":
            # Get selected GCF IDs and their corresponding data
            selected_items = {
                row["GCF ID"]: {
                    "MiBIG IDs": row["MiBIG IDs"],
                    "BGC Classes": row["BGC Classes"],
                }
                for i, row in enumerate(virtual_data)
                if i in selected_rows
            }
            id_field = "gcf_id"
            item_field = "spectrum"
            score_field = "score"
        else:  # MG
            # Get selected MF IDs
            selected_items = {
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
            id_field = "mf_id"
            item_field = "gcf"
            score_field = "score"

        # Convert links data to DataFrame
        links_df = pd.DataFrame(links_data)

        # Apply scoring filters
        filtered_df = scoring_apply(links_df, dropdown_menus, radiobuttons, cutoffs_met)

        # Filter once for all selected items
        filtered_df = filtered_df[filtered_df[id_field].isin(selected_items.keys())]

        if filtered_df.empty:
            return (
                f"No matching links found for selected {item_type}s.",
                True,
                [],
                [],
                {"display": "none"},
                {"color": "#888888"},
                True,
                None,
                {},
            )

        # Prepare for results using vectorized operations
        results = []
        detailed_data = {}  # Only store additional data needed for Excel export

        # Group by the ID field
        for item_id, group in filtered_df.groupby(id_field):
            # Sort by score in descending order
            group = group.sort_values(score_field, ascending=False)

            # Calculate aggregate values once per group
            avg_score = round(group[score_field].mean(), 2)
            n_links = len(group)

            # Get the highest score
            highest_score = group[score_field].max()

            # Get all items with the highest score - as a DataFrame
            top_items = group[group[score_field] == highest_score]

            # Process all top items at once using vectorized operations
            if prefix == "gm":
                # Convert to dictionary format for faster processing
                top_items_dict = top_items.to_dict("records")

                # Only create the extra data field once per GCF ID
                detailed_data[str(item_id)] = {
                    "spectrum_ids_str": "|".join([str(s.get("id", "")) for s in group[item_field]]),
                    "spectrum_mf_ids_str": "|".join(
                        [str(s.get("mf_id", "None")) for s in group[item_field]]
                    ),
                    "spectrum_scores_str": "|".join(
                        [str(score) for score in group[score_field].tolist()]
                    ),
                    "spectrum_mz_str": "|".join(
                        [str(s.get("precursor_mz", "None")) for s in group[item_field]]
                    ),
                    "spectrum_gnps_id_str": "|".join(
                        [str(s.get("gnps_id", "None")) for s in group[item_field]]
                    ),
                }

                # Create results for each top item
                for top_item in top_items_dict:
                    spectrum_data = top_item[item_field]
                    result = {
                        # Mandatory fields
                        "GCF ID": int(item_id) if pd.notna(item_id) else float("nan"),  # type: ignore
                        "# Links": n_links,
                        "Average Score": avg_score,
                        # Optional fields
                        "Top Spectrum ID": int(spectrum_data.get("id", float("nan")))
                        if spectrum_data.get("id") is not None
                        else float("nan"),
                        "Top Spectrum MF ID": int(spectrum_data.get("mf_id", float("nan")))
                        if spectrum_data.get("mf_id") is not None
                        else float("nan"),
                        "Top Spectrum Precursor m/z": round(
                            spectrum_data.get("precursor_mz", float("nan")), 4
                        )
                        if spectrum_data.get("precursor_mz") is not None
                        else float("nan"),
                        "Top Spectrum GNPS ID": spectrum_data.get("gnps_id", "None")
                        if spectrum_data.get("gnps_id") is not None
                        else "None",
                        "Top Spectrum Score": round(top_item.get(score_field, float("nan")), 4)
                        if top_item.get(score_field) is not None
                        else float("nan"),
                        "MiBIG IDs": selected_items[item_id]["MiBIG IDs"],
                        "BGC Classes": selected_items[item_id]["BGC Classes"],
                    }
                    results.append(result)
            else:  # MG
                # Convert to dictionary format for faster processing
                top_items_dict = top_items.to_dict("records")

                # Only create the extra data field once per MF ID
                detailed_data[str(item_id)] = {
                    "gcf_ids_str": "|".join([str(gcf.get("id", "")) for gcf in group[item_field]]),
                    "gcf_scores_str": "|".join(
                        [str(score) for score in group[score_field].tolist()]
                    ),
                    "gcf_bgc_classes_str": "|".join(
                        [
                            ", ".join(
                                {item for sublist in gcf.get("BGC Classes", []) for item in sublist}
                            )
                            for gcf in group[item_field]
                        ]
                    ),
                    "gcf_bgc_ids_str": "|".join(
                        [
                            ", ".join([str(bgc_id) for bgc_id in gcf.get("BGC IDs", [])])
                            for gcf in group[item_field]
                        ]
                    ),
                    "gcf_num_bgcs_str": "|".join(
                        [str(gcf.get("# BGCs", 0)) for gcf in group[item_field]]
                    ),
                }

                # Create results for each top item
                for top_item in top_items_dict:
                    gcf_data = top_item[item_field]
                    result = {
                        # Mandatory fields
                        "MF ID": int(item_id) if pd.notna(item_id) else float("nan"),  # type: ignore
                        "# Links": n_links,
                        "Average Score": avg_score,
                        # Optional fields
                        "Top GCF ID": int(gcf_data.get("id", float("nan")))
                        if gcf_data.get("id") is not None
                        else float("nan"),
                        "Top GCF # BGCs": gcf_data.get("# BGCs", 0),
                        "Top GCF BGC IDs": ", ".join([str(s) for s in gcf_data.get("BGC IDs", [])]),
                        "Top GCF BGC Classes": ", ".join(
                            {
                                item
                                for sublist in gcf_data.get("BGC Classes", [])
                                for item in sublist
                            }
                        ),
                        "Top GCF Score": round(top_item.get(score_field, float("nan")), 4),
                    }
                    results.append(result)

        tooltip_data = []
        # Only generate tooltips if we have a reasonable number of rows
        if len(results) > MAX_TOOLTIP_ROWS:
            alert_message = f"Tooltips disabled for performance (showing {len(results)} rows)."
        else:
            # Prepare tooltip data
            alert_message = ""
            for result in results:
                if prefix == "gm":
                    # Get the detailed data for this result
                    detail = detailed_data.get(str(result["GCF ID"]), {})
                    ids = (
                        detail.get("spectrum_ids_str", "").split("|")
                        if detail.get("spectrum_ids_str")
                        else []
                    )
                    scores = (
                        [float(s) for s in detail.get("spectrum_scores_str", "").split("|")]
                        if detail.get("spectrum_scores_str")
                        else []
                    )
                    mf_ids = (
                        detail.get("spectrum_mf_ids_str", "").split("|")
                        if detail.get("spectrum_mf_ids_str")
                        else []
                    )
                else:  # MG
                    # Get the detailed data for this result
                    detail = detailed_data.get(str(result["MF ID"]), {})
                    ids = (
                        detail.get("gcf_ids_str", "").split("|")
                        if detail.get("gcf_ids_str")
                        else []
                    )
                    scores = (
                        [float(s) for s in detail.get("gcf_scores_str", "").split("|")]
                        if detail.get("gcf_scores_str")
                        else []
                    )

                # Show only top 5 items in tooltip
                max_tooltip_entries = 5
                total_entries = len(ids)

                if prefix == "gm":
                    items_table = "| Spectrum ID | MF ID | Score |\n|--------|--------|--------|\n"

                    # Add top entries for GM tab
                    for idx in range(min(max_tooltip_entries, len(ids))):
                        item_id = ids[idx] if idx < len(ids) else ""
                        score = scores[idx] if idx < len(scores) else 0
                        mf_id = mf_ids[idx] if idx < len(mf_ids) else ""
                        items_table += f"| {item_id} | {mf_id} | {round(float(score), 4)} |\n"
                else:
                    items_table = "| GCF ID | Score |\n|--------|--------|\n"
                    # Add top entries for MG tab
                    for idx in range(min(max_tooltip_entries, len(ids))):
                        item_id = ids[idx] if idx < len(ids) else ""
                        score = scores[idx] if idx < len(scores) else 0
                        items_table += f"| {item_id} | {round(float(score), 4)} |\n"

                # Add indication of more entries if applicable
                if total_entries > max_tooltip_entries:
                    remaining = total_entries - max_tooltip_entries
                    items_table += f"\n... {remaining} more entries ..."

                row_tooltip = {
                    "# Links": {"value": items_table, "type": "markdown"},
                }
                tooltip_data.append(row_tooltip)

        return (
            alert_message,
            alert_message != "",
            results,
            tooltip_data,
            {"display": "block"},
            {},
            False,
            None,
            detailed_data,
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
            None,
            {},
        )


def toggle_column_settings_modal(n1, n2, is_open):
    """Toggle the visibility of the column settings modal.

    Generic function to handle both GM and MG column settings modal toggling.

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


def update_columns(
    selected_columns: list[str] | None,
    n_clicks: int | None,
    mandatory_columns: list[dict],
    optional_columns: list[dict],
) -> list[dict]:
    """Update the columns of the results table based on user selections.

    Generic function to handle both GM and MG column updates.

    Args:
        selected_columns: List of selected columns to display.
        n_clicks: Number of times the "Show Results" button has been clicked.
        mandatory_columns: List of mandatory column definitions.
        optional_columns: List of optional column definitions.

    Returns:
        List of column definitions for the results table.
    """
    # Start with mandatory columns
    columns: list[dict] = mandatory_columns.copy()

    # Create a dictionary for optional columns lookup
    optional_columns_dict = {col["id"]: col for col in optional_columns}

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


def toggle_download_button(table_data):
    """Enable/disable download button based on data availability.

    Generic function to handle both GM and MG download button toggling.

    Args:
        table_data: Current data in the results table.

    Returns:
        Tuple containing disabled state, alert visibility, and alert message.
    """
    if not table_data:
        return True, False, ""
    return False, False, ""


def generate_excel(n_clicks, table_data, detailed_data, tab_prefix):
    """Generate Excel file with two sheets: full results and detailed data.

    Args:
        n_clicks: Number of clicks on the download button.
        table_data: Data from the results table.
        detailed_data: Detailed data for each row in the table.
        tab_prefix: Tab prefix ('gm' or 'mg').

    Returns:
        Tuple containing the download component, alert visibility, alert message, and spinner state.
    """
    if not ctx.triggered or not table_data:
        return None, False, "", None

    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Sheet 1: Best candidate links table
            results_df = pd.DataFrame(table_data)
            results_df.to_excel(writer, sheet_name="Best Candidate Links", index=False)

            # Sheet 2: Detailed data
            detailed_data_list = []

            # Get unique primary IDs to avoid redundant processing
            if tab_prefix == "gm":
                unique_primary_ids = {row["GCF ID"] for row in table_data}
            else:  # MG
                unique_primary_ids = {row["MF ID"] for row in table_data}

            # Process each unique primary ID only once
            for primary_id in unique_primary_ids:
                if tab_prefix == "gm":
                    detail = detailed_data.get(str(primary_id), {})

                    if not detail:
                        continue

                    ids = (
                        [
                            int(s) if s and s != "None" else float("nan")
                            for s in detail.get("spectrum_ids_str", "").split("|")
                        ]
                        if detail.get("spectrum_ids_str")
                        else []
                    )
                    mf_ids = (
                        [
                            int(s) if s and s != "None" else float("nan")
                            for s in detail.get("spectrum_mf_ids_str", "").split("|")
                        ]
                        if detail.get("spectrum_mf_ids_str")
                        else []
                    )
                    scores = (
                        [
                            float(s) if s and s != "None" else float("nan")
                            for s in detail.get("spectrum_scores_str", "").split("|")
                        ]
                        if detail.get("spectrum_scores_str")
                        else []
                    )
                    mz_values = (
                        [
                            float(s) if s and s != "None" else float("nan")
                            for s in detail.get("spectrum_mz_str", "").split("|")
                        ]
                        if detail.get("spectrum_mz_str")
                        else []
                    )
                    gnps_ids = (
                        detail.get("spectrum_gnps_id_str", "").split("|")
                        if detail.get("spectrum_gnps_id_str")
                        else []
                    )

                    # Add all entries without truncation
                    for item_id, mf_id, score, mz, gnps_id in zip(
                        ids, mf_ids, scores, mz_values, gnps_ids
                    ):
                        detail_row = {
                            "GCF ID": primary_id,
                            "Spectrum ID": item_id,
                            "MF ID": mf_id,
                            "Score": score,
                            "Precursor m/z": mz,
                            "GNPS ID": gnps_id,
                        }
                        detailed_data_list.append(detail_row)
                else:  # MG
                    detail = detailed_data.get(str(primary_id), {})

                    if not detail:
                        continue

                    ids = (
                        detail.get("gcf_ids_str", "").split("|")
                        if detail.get("gcf_ids_str")
                        else []
                    )
                    scores = (
                        [float(s) for s in detail.get("gcf_scores_str", "").split("|")]
                        if detail.get("gcf_scores_str")
                        else []
                    )
                    bgc_classes = (
                        detail.get("gcf_bgc_classes_str", "").split("|")
                        if detail.get("gcf_bgc_classes_str")
                        else []
                    )
                    bgc_ids = (
                        detail.get("gcf_bgc_ids_str", "").split("|")
                        if detail.get("gcf_bgc_ids_str")
                        else []
                    )
                    num_bgcs = (
                        [
                            int(s) if s and s.isdigit() else 0
                            for s in detail.get("gcf_num_bgcs_str", "").split("|")
                        ]
                        if detail.get("gcf_num_bgcs_str")
                        else []
                    )

                    # Add all entries without truncation
                    for item_id, score, bgc_class, bgc_id, num_bgc in zip(
                        ids, scores, bgc_classes, bgc_ids, num_bgcs
                    ):
                        detail_row = {
                            "MF ID": primary_id,
                            "GCF ID": int(item_id) if item_id.isdigit() else item_id,
                            "Score": score,
                            "BGC Classes": bgc_class,
                            "BGC IDs": bgc_id,
                            "# BGCs": num_bgc,
                        }
                        detailed_data_list.append(detail_row)

            if detailed_data_list:
                detailed_df = pd.DataFrame(detailed_data_list)
                detail_sheet_name = "All Candidate Links"
                detailed_df.to_excel(writer, sheet_name=detail_sheet_name, index=False)

        # Prepare the file for download
        excel_data = output.getvalue()
        filename = (
            f"nplinker_{'genom_to_metabol' if tab_prefix == 'gm' else 'metabol_to_genom'}.xlsx"
        )
        return dcc.send_bytes(excel_data, filename), False, "", None
    except Exception as e:
        return None, True, f"Error generating Excel file: {str(e)}", None


# ------------------ GM Results table functions ------------------ #
@app.callback(
    Output("gm-results-table-column-settings-modal", "is_open"),
    [
        Input("gm-results-table-column-settings-button", "n_clicks"),
        Input("gm-results-table-column-settings-close", "n_clicks"),
    ],
    [State("gm-results-table-column-settings-modal", "is_open")],
)
def gm_toggle_column_settings_modal(n1, n2, is_open):
    """Toggle the visibility of the GM column settings modal.

    Args:
        n1: Number of clicks on the open button.
        n2: Number of clicks on the close button.
        is_open: Current state of the modal (open or closed).

    Returns:
        The new state of the modal (open or closed).
    """
    return toggle_column_settings_modal(n1, n2, is_open)


@app.callback(
    Output("gm-results-table", "columns"),
    [
        Input("gm-results-table-column-toggle", "value"),
        Input("gm-results-button", "n_clicks"),
    ],
)
def gm_update_columns(selected_columns: list[str] | None, n_clicks: int | None) -> list[dict]:
    """Update the columns of the GM results table based on user selections.

    Args:
        selected_columns: List of selected columns to display.
        n_clicks: Number of times the "Show Results" button has been clicked.

    Returns:
        List of column definitions for the results table.
    """
    return update_columns(
        selected_columns,
        n_clicks,
        GM_RESULTS_TABLE_MANDATORY_COLUMNS,
        GM_RESULTS_TABLE_OPTIONAL_COLUMNS,
    )


@app.callback(
    Output("gm-results-alert", "children"),
    Output("gm-results-alert", "is_open"),
    Output("gm-results-table", "data"),
    Output("gm-results-table", "tooltip_data"),
    Output("gm-results-table-card-body", "style"),
    Output("gm-results-table-card-header", "style"),
    Output("gm-results-table-column-settings-button", "disabled"),
    Output("loading-spinner-container", "children", allow_duplicate=True),
    Output("gm-detailed-data-store", "data"),
    Input("gm-results-button", "n_clicks"),
    Input("gm-table", "derived_virtual_data"),
    Input("gm-table", "derived_virtual_selected_rows"),
    State("processed-links-store", "data"),
    State({"type": "gm-scoring-dropdown-menu", "index": ALL}, "value"),
    State({"type": "gm-scoring-radio-items", "index": ALL}, "value"),
    State({"type": "gm-scoring-dropdown-ids-cutoff-met", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def gm_update_results_datatable(
    n_clicks,
    virtual_data,
    selected_rows,
    processed_links,
    dropdown_menus,
    radiobuttons,
    cutoffs_met,
):
    """Update the GM results DataTable based on scoring filters."""
    return update_results_datatable(
        n_clicks,
        virtual_data,
        selected_rows,
        processed_links,
        dropdown_menus,
        radiobuttons,
        cutoffs_met,
        "gm",
        "GCF",
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
def gm_toggle_download_button(table_data):
    """Enable/disable download button for GM tab based on data availability."""
    return toggle_download_button(table_data)


@app.callback(
    [
        Output("gm-download-excel", "data"),
        Output("gm-download-alert", "is_open", allow_duplicate=True),
        Output("gm-download-alert", "children", allow_duplicate=True),
        Output("loading-spinner-container", "children", allow_duplicate=True),
    ],
    Input("gm-download-button", "n_clicks"),
    [
        State("gm-results-table", "data"),
        State("gm-detailed-data-store", "data"),
    ],
    prevent_initial_call=True,
)
def gm_generate_excel(n_clicks, table_data, detailed_data):
    """Generate Excel file for GM data."""
    return generate_excel(n_clicks, table_data, detailed_data, "gm")


# ------------------ MG Results table functions ------------------ #
@app.callback(
    Output("mg-results-table-column-settings-modal", "is_open"),
    [
        Input("mg-results-table-column-settings-button", "n_clicks"),
        Input("mg-results-table-column-settings-close", "n_clicks"),
    ],
    [State("mg-results-table-column-settings-modal", "is_open")],
)
def mg_toggle_column_settings_modal(n1, n2, is_open):
    """Toggle the visibility of the MG column settings modal.

    Args:
        n1: Number of clicks on the open button.
        n2: Number of clicks on the close button.
        is_open: Current state of the modal (open or closed).

    Returns:
        The new state of the modal (open or closed).
    """
    return toggle_column_settings_modal(n1, n2, is_open)


@app.callback(
    Output("mg-results-table", "columns"),
    [
        Input("mg-results-table-column-toggle", "value"),
        Input("mg-results-button", "n_clicks"),
    ],
)
def mg_update_columns(selected_columns: list[str] | None, n_clicks: int | None) -> list[dict]:
    """Update the columns of the MG results table based on user selections.

    Args:
        selected_columns: List of selected columns to display.
        n_clicks: Number of times the "Show Results" button has been clicked.

    Returns:
        List of column definitions for the results table.
    """
    return update_columns(
        selected_columns,
        n_clicks,
        MG_RESULTS_TABLE_MANDATORY_COLUMNS,
        MG_RESULTS_TABLE_OPTIONAL_COLUMNS,
    )


@app.callback(
    Output("mg-results-alert", "children"),
    Output("mg-results-alert", "is_open"),
    Output("mg-results-table", "data"),
    Output("mg-results-table", "tooltip_data"),
    Output("mg-results-table-card-body", "style"),
    Output("mg-results-table-card-header", "style"),
    Output("mg-results-table-column-settings-button", "disabled"),
    Output("loading-spinner-container", "children", allow_duplicate=True),
    Output("mg-detailed-data-store", "data"),
    Input("mg-results-button", "n_clicks"),
    Input("mg-table", "derived_virtual_data"),
    Input("mg-table", "derived_virtual_selected_rows"),
    State("processed-links-store", "data"),
    State({"type": "mg-scoring-dropdown-menu", "index": ALL}, "value"),
    State({"type": "mg-scoring-radio-items", "index": ALL}, "value"),
    State({"type": "mg-scoring-dropdown-ids-cutoff-met", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def mg_update_results_datatable(
    n_clicks,
    virtual_data,
    selected_rows,
    processed_links,
    dropdown_menus,
    radiobuttons,
    cutoffs_met,
):
    """Update the MG results DataTable based on scoring filters."""
    return update_results_datatable(
        n_clicks,
        virtual_data,
        selected_rows,
        processed_links,
        dropdown_menus,
        radiobuttons,
        cutoffs_met,
        "mg",
        "MF",
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
def mg_toggle_download_button(table_data):
    """Enable/disable download button for MG tab based on data availability."""
    return toggle_download_button(table_data)


@app.callback(
    [
        Output("mg-download-excel", "data"),
        Output("mg-download-alert", "is_open", allow_duplicate=True),
        Output("mg-download-alert", "children", allow_duplicate=True),
        Output("loading-spinner-container", "children", allow_duplicate=True),
    ],
    Input("mg-download-button", "n_clicks"),
    [
        State("mg-results-table", "data"),
        State("mg-detailed-data-store", "data"),
    ],
    prevent_initial_call=True,
)
def mg_generate_excel(n_clicks, table_data, detailed_data):
    """Generate Excel file for MG data."""
    return generate_excel(n_clicks, table_data, detailed_data, "mg")
