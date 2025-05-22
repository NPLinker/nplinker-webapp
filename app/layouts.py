import uuid
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
from config import GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from config import MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from config import MIBIG_VERSIONS
from dash import dash_table
from dash import dcc
from dash import html


# ------------------ Helper Functions ------------------ #
def create_data_table(table_id, select_all_id):
    """Create a common data table component.

    Args:
        table_id: The ID for the table component.
        select_all_id: The ID for the select-all checkbox.

    Returns:
        A dash_table.DataTable component.
    """
    return dash_table.DataTable(
        id=table_id,
        columns=[],
        data=[],
        tooltip_data=[],
        editable=False,
        filter_action="none",
        sort_action="none",
        sort_mode="multi",
        column_selectable=False,
        row_deletable=False,
        row_selectable="multi",
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=10,
        style_cell={
            "textAlign": "left",
            "padding": "5px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "minWidth": "80px",
            "width": "auto",
            "maxWidth": "200px",
        },
        style_header={
            "backgroundColor": "#FF6E42",
            "fontWeight": "bold",
            "color": "white",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data={
            "border": "1px solid #ddd",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data_conditional=[
            {
                "if": {"state": "selected"},
                "backgroundColor": "white",
                "border": "1px solid #ddd",
            }
        ],
        style_cell_conditional=[{"if": {"column_id": "selector"}, "width": "30px"}],
        tooltip_delay=0,
        tooltip_duration=None,
        css=[
            {
                "selector": ".dash-table-tooltip",
                "rule": """
                    background-color: #ffd8cc;
                    font-family: monospace;
                    font-size: 12px;
                    max-width: none !important;
                    white-space: pre-wrap;
                    padding: 8px;
                    border: 1px solid #FF6E42;
                    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
                """,
            }
        ],
        tooltip={"type": "markdown"},
    )


def create_results_table(table_id, no_sort_columns):
    """Create a common results table component.

    Args:
        table_id: The ID for the table component.
        no_sort_columns: List of column names that should not be sortable.

    Returns:
        A dash_table.DataTable component.
    """
    return dash_table.DataTable(
        id=table_id,
        columns=[],
        data=[],
        editable=False,
        filter_action="none",
        sort_action="native",
        virtualization=True,
        fixed_rows={"headers": True},  # Keep headers visible when scrolling
        sort_mode="single",
        sort_as_null=["None", ""],
        sort_by=[],
        page_action="native",
        page_current=0,
        page_size=50,
        style_table={"width": "100%", "overflowX": "auto", "overflowY": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "5px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "minWidth": "80px",
            "width": "auto",
            "maxWidth": "200px",
        },
        style_header={
            "backgroundColor": "#FF6E42",
            "fontWeight": "bold",
            "color": "white",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data={
            "border": "1px solid #ddd",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data_conditional=[
            {
                "if": {"state": "selected"},
                "backgroundColor": "white",
                "border": "1px solid #ddd",
            }
        ],
        tooltip_delay=0,
        tooltip_duration=None,
        css=(
            [
                {
                    "selector": ".dash-table-tooltip",
                    "rule": """
                        background-color: #ffd8cc;
                        font-family: monospace;
                        font-size: 12px;
                        max-width: none !important;
                        white-space: pre-wrap;
                        padding: 8px;
                        border: 1px solid #FF6E42;
                        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
                    """,
                }
            ]
            + [
                {
                    "selector": f'th[data-dash-column="{col}"] span.column-header--sort',
                    "rule": "display: none",
                }
                for col in no_sort_columns
            ]
            + [
                # Style sort arrow hover state
                {
                    "selector": ".column-header--sort:hover",
                    "rule": "color: white !important;",
                }
            ]
        ),
        tooltip={"type": "markdown"},
    )


def create_filter_accordion(
    title,
    control_id,
    blocks_store_id,
    blocks_container_id,
    apply_button_id,
    include_mibig_selector=False,
):
    """Create a common filter accordion component.

    Args:
        title: The title for the accordion.
        control_id: The ID for the accordion control.
        blocks_store_id: The ID for blocks storage.
        blocks_container_id: The ID for blocks container.
        apply_button_id: The ID for the apply button.
        include_mibig_selector: Whether to include MIBiG version selector.

    Returns:
        A dmc.Accordion component.
    """
    panel_content = []

    # Add MIBiG version selector if needed
    if include_mibig_selector:
        panel_content.append(
            dbc.Row(
                dbc.Col(
                    html.Div(
                        [
                            dbc.Label(
                                "MIBiG Version:",
                                className="me-2",
                                style={"verticalAlign": "middle"},
                            ),
                            dcc.Dropdown(
                                id="mibig-version-selector",
                                options=MIBIG_VERSIONS,
                                value="pre_v4",  # Default to pre v4.0 for backward compatibility
                                clearable=False,
                                style={
                                    "width": "150px",
                                    "verticalAlign": "middle",
                                    "marginLeft": "5px",
                                },
                            ),
                        ],
                        className="d-flex align-items-center",
                        style={"marginLeft": "0", "marginBottom": "70px"},
                    ),
                    width=12,
                ),
                className="mb-3",
            )
        )

    panel_content.extend(
        [
            html.Div(
                [
                    dcc.Store(id=blocks_store_id, data=[]),
                    html.Div(
                        id=blocks_container_id,
                        children=[],
                    ),
                ]
            ),
            html.Div(
                dbc.Button(
                    "Apply Filters",
                    id=apply_button_id,
                    color="primary",
                    className="mt-3",
                ),
                className="d-flex justify-content-center",
            ),
        ]
    )

    return dmc.Accordion(
        [
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        title,
                        disabled=True,
                        id=control_id,
                        className="mt-5 mb-3",
                    ),
                    dmc.AccordionPanel(panel_content),
                ],
                value=f"{control_id.split('-')[0]}-filter-accordion",
            ),
        ],
        value=[],
        className="mt-5 mb-3",
        id=f"{control_id.split('-')[0]}-filter-accordion-component",
    )


def create_scoring_accordion(control_id, blocks_store_id, blocks_container_id):
    """Create a common scoring accordion component.

    Args:
        control_id: The ID for the accordion control.
        blocks_store_id: The ID for blocks storage.
        blocks_container_id: The ID for blocks container.

    Returns:
        A dmc.Accordion component.
    """
    return dmc.Accordion(
        [
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        "Scoring",
                        disabled=True,
                        id=control_id,
                        className="mt-5 mb-3",
                    ),
                    dmc.AccordionPanel(
                        [
                            html.Div(
                                [
                                    dcc.Store(id=blocks_store_id, data=[]),
                                    html.Div(
                                        id=blocks_container_id,
                                        children=[],
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                value=f"{control_id.split('-')[0]}-scoring-accordion",
            ),
        ],
        value=[],
        className="mt-5 mb-3",
        id=f"{control_id.split('-')[0]}-scoring-accordion-component",
    )


def create_results_section(  # noqa: D417
    button_id,
    alert_id,
    table_id,
    table_header_id,
    table_body_id,
    settings_button_id,
    settings_modal_id,
    settings_close_id,
    column_toggle_id,
    checkl_options,
    download_button_id,
    download_alert_id,
    download_id,
    no_sort_columns,
):
    """Create a common results section.

    Args:
        Various IDs for components and configuration.

    Returns:
        A list of components for the results section.
    """
    results = html.Div(
        [
            html.Div(
                dbc.Button(
                    "Show Results",
                    id=button_id,
                    color="primary",
                    className="mt-3",
                    disabled=True,
                ),
                className="d-flex justify-content-center",
            ),
            html.Div(
                dbc.Alert(
                    "Your alert message here",
                    id=alert_id,
                    color="warning",
                    className="mt-3 text-center w-75 mx-auto",
                    is_open=False,
                ),
                className="d-flex justify-content-center",
            ),
        ]
    )

    results_table = dbc.Card(
        [
            dbc.CardHeader(
                [
                    "Candidate Links",
                    dbc.Button(
                        "Columns settings",
                        id=settings_button_id,
                        color="secondary",
                        size="sm",
                        className="float-end",
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader("Select columns to display"),
                            dbc.ModalBody(
                                dbc.Checklist(
                                    id=column_toggle_id,
                                    options=checkl_options,
                                    value=[checkl_options[0]],
                                    switch=True,
                                )
                            ),
                            dbc.ModalFooter(
                                dbc.Button(
                                    "Close",
                                    id=settings_close_id,
                                    className="ms-auto",
                                )
                            ),
                        ],
                        id=settings_modal_id,
                        is_open=False,
                    ),
                ],
                id=table_header_id,
                style={"color": "#888888"},
            ),
            dbc.CardBody(
                [
                    create_results_table(table_id, no_sort_columns),
                ],
                id=table_body_id,
                style={"display": "none"},
            ),
        ]
    )

    results_download = html.Div(
        [
            html.Div(
                dbc.Button(
                    "Download Results (Excel)",
                    id=download_button_id,
                    color="primary",
                    className="mt-3",
                    disabled=True,
                ),
                className="d-flex justify-content-center",
            ),
            html.Div(
                dbc.Alert(
                    "Error downloading results",
                    id=download_alert_id,
                    color="warning",
                    className="mt-3 text-center w-75 mx-auto",
                    is_open=False,
                ),
                className="d-flex justify-content-center",
            ),
            dcc.Download(id=download_id),
        ]
    )

    return [results, results_table, results_download]


def create_data_table_card(table_id, header_id, body_id, select_all_id, output1_id, output2_id):  # noqa: D417
    """Create a common data table card.

    Args:
        Various IDs for components.

    Returns:
        A dbc.Card component.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    "Data",
                ],
                id=header_id,
                style={"color": "#888888"},
            ),
            dbc.CardBody(
                [
                    html.Div(
                        dcc.Checklist(
                            options=[{"label": "", "value": "disabled"}],
                            id=select_all_id,
                            style={
                                "position": "absolute",
                                "top": "4px",
                                "left": "10px",
                                "zIndex": "1000",
                            },
                        ),
                        style={"position": "relative", "height": "0px"},
                    ),
                    create_data_table(table_id, select_all_id),
                ],
                id=body_id,
                style={"display": "none"},
            ),
            html.Div(id=output1_id, className="p-4"),
            html.Div(id=output2_id, className="p-4"),
        ]
    )


def create_tab_content(prefix, filter_title, checkl_options, no_sort_columns):
    """Create tab content for GM or MG tabs.

    Args:
        prefix: The prefix for component IDs ('gm' or 'mg').
        filter_title: The title for the filter accordion.
        checkl_options: Options for the column settings checklist.
        no_sort_columns: Columns that should not be sortable in results table.

    Returns:
        A dbc.Row component with all tab content.
    """
    # Create filter accordion with MIBiG selector for GM tab
    filter_accordion = create_filter_accordion(
        filter_title,
        f"{prefix}-filter-accordion-control",
        f"{prefix}-filter-blocks-id",
        f"{prefix}-filter-blocks-container",
        f"{prefix}-filter-apply-button",
        include_mibig_selector=(prefix == "gm"),
    )

    # Create data table
    data_table = create_data_table_card(
        f"{prefix}-table",
        f"{prefix}-table-card-header",
        f"{prefix}-table-card-body",
        f"{prefix}-table-select-all-checkbox",
        f"{prefix}-table-output1",
        f"{prefix}-table-output2",
    )

    # Create scoring accordion
    scoring_accordion = create_scoring_accordion(
        f"{prefix}-scoring-accordion-control",
        f"{prefix}-scoring-blocks-id",
        f"{prefix}-scoring-blocks-container",
    )

    # Create results section
    results_components = create_results_section(
        f"{prefix}-results-button",
        f"{prefix}-results-alert",
        f"{prefix}-results-table",
        f"{prefix}-results-table-card-header",
        f"{prefix}-results-table-card-body",
        f"{prefix}-results-table-column-settings-button",
        f"{prefix}-results-table-column-settings-modal",
        f"{prefix}-results-table-column-settings-close",
        f"{prefix}-results-table-column-toggle",
        checkl_options,
        f"{prefix}-download-button",
        f"{prefix}-download-alert",
        f"{prefix}-download-excel",
        no_sort_columns,
    )

    # Add graph component only for GM tab
    components = []
    if prefix == "gm":
        # Add x-axis selector dropdown above the graph
        graph_with_selector = html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Label("Select X-axis: ", className="me-2"),
                                    dcc.Dropdown(
                                        id="gm-graph-x-axis-selector",
                                        options=[
                                            {"label": "# BGCs", "value": "n_bgcs"},
                                            {"label": "BGC Classes", "value": "class_bgcs"},
                                        ],
                                        value="n_bgcs",  # Default value
                                        clearable=False,
                                        style={"width": "200px"},
                                    ),
                                ],
                                className="d-flex align-items-center",
                            ),
                            width=12,
                        )
                    ],
                    id="gm-graph-selector-container",
                ),
                dcc.Graph(id="gm-graph"),
            ],
            className="mt-5 mb-3",
        )

        components = [
            dbc.Col(filter_accordion, width=10, className="mx-auto dbc"),
            dbc.Col(graph_with_selector, width=10, className="mx-auto dbc"),
            dbc.Col(data_table, width=10, className="mx-auto"),
            dbc.Col(scoring_accordion, width=10, className="mx-auto dbc"),
        ]
    else:
        components = [
            dbc.Col(filter_accordion, width=10, className="mx-auto dbc"),
            dbc.Col(data_table, width=10, className="mx-auto"),
            dbc.Col(scoring_accordion, width=10, className="mx-auto dbc"),
        ]

    # Add results components
    for component in results_components:
        components.append(dbc.Col(component, width=10, className="mt-3 mx-auto"))

    return dbc.Row(components)


# ------------------ Nav Bar ------------------ #
navbar = dbc.Row(
    dbc.Col(
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Doc", href="https://nplinker.github.io/nplinker/latest/")),
                dbc.NavItem(
                    dbc.NavLink("About", href="https://github.com/NPLinker/nplinker-webapp"),
                ),
            ],
            brand="NPLinker Webapp",
            color="primary",
            className="p-3 mb-2",
            dark=True,
        ),
    ),
)


# ------------------ Uploader ------------------ #
uploader = html.Div(
    [
        dbc.Row(
            dbc.Col(
                du.Upload(
                    id="dash-uploader",
                    text="Import Data",
                    text_completed="Uploaded: ",
                    filetypes=["pkl", "pickle"],
                    upload_id=uuid.uuid1(),  # Unique session id
                    cancel_button=True,
                    max_files=1,
                ),
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(children="No file uploaded", id="dash-uploader-output", className="p-4"),
                className="d-flex justify-content-center",
            )
        ),
        # Demo data button
        dbc.Row(
            dbc.Col(
                html.Div(
                    dbc.Button(
                        "Load Demo Data",
                        id="demo-data-button",
                        color="primary",
                        className="mt-3",
                    ),
                    className="d-flex justify-content-center",
                ),
                className="d-flex justify-content-center",
            )
        ),
        dcc.Store(id="file-store"),  # Store to keep the file contents
        dcc.Store(id="processed-data-store"),  # Store to keep the processed data
        dcc.Store(id="processed-links-store"),  # Store to keep the processed links
        dcc.Store(id="gm-detailed-data-store"),  # Store for GM detailed data
        dcc.Store(id="mg-detailed-data-store"),  # Store for MG detailed data
    ],
    className="p-5 ml-5 mr-5",
)

loading_spinner = dbc.Spinner(
    html.Div(id="loading-spinner-container"),
    color="primary",
    size="lg",
    type="border",
    fullscreen=True,
    fullscreen_style={
        "backgroundColor": "rgba(0, 0, 0, 0.3)",
        "zIndex": "9999",
    },
)

# ------------------ Tab Content Configuration ------------------ #
# No-sort columns definitions
gm_no_sort_columns = [
    "GCF ID",
    "# Links",
    "Average Score",
    "Top Spectrum ID",
    "Top Spectrum MF ID",
    "Top Spectrum GNPS ID",
    "MiBIG IDs",
    "BGC Classes",
]

mg_no_sort_columns = [
    "MF ID",
    "# Links",
    "Average Score",
    "Top GCF ID",
    "Top GCF # BGCs",
    "Top GCF BGC IDs",
    "Top GCF BGC Classes",
]

# ------------------ Tab Content Creation ------------------ #
# Create tab content
gm_content = create_tab_content(
    "gm", "Genomics filter", GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS, gm_no_sort_columns
)

mg_content = create_tab_content(
    "mg", "Metabolomics filter", MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS, mg_no_sort_columns
)

# ------------------ Tabs ------------------ #
tabs = dbc.Row(
    dbc.Col(
        dbc.Tabs(
            [
                dbc.Tab(
                    gm_content,
                    label="Genomics -> Metabolomics",
                    activeTabClassName="fw-bold",
                    disabled=True,
                    id="gm-tab",
                ),
                dbc.Tab(
                    mg_content,
                    label="Metabolomics -> Genomics",
                    activeTabClassName="fw-bold",
                    disabled=True,
                    id="mg-tab",
                ),
            ],
        ),
    ),
    className="p-5",
)


# ------------------ Layout Function ------------------ #
def create_layout():  # noqa: D103
    return dmc.MantineProvider(
        [dbc.Container([navbar, uploader, loading_spinner, tabs], fluid=True, className="p-0")]
    )
