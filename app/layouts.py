import uuid
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
from config import GM_DROPDOWN_BGC_CLASS_OPTIONS
from config import GM_DROPDOWN_BGC_CLASS_PLACEHOLDER
from config import GM_DROPDOWN_MENU_OPTIONS
from config import GM_TEXT_INPUT_IDS_PLACEHOLDER
from dash import dcc
from dash import html


# ------------------ Nav Bar ------------------ #
color_mode_switch = html.Span(
    [
        dbc.Label(className="fa fa-moon", html_for="color-mode-switch"),
        dbc.Switch(
            id="color-mode-switch",
            value=False,
            className="d-inline-block ms-1",
            persistence=True,
        ),
        dbc.Label(className="fa fa-sun", html_for="color-mode-switch"),
    ],
    className="p-2",
)
navbar = dbc.Row(
    dbc.Col(
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Doc", href="https://nplinker.github.io/nplinker/latest/")),
                dbc.NavItem(
                    dbc.NavLink("About", href="https://github.com/NPLinker/nplinker-webapp"),
                ),
                dbc.NavItem(
                    color_mode_switch,
                    className="mt-1 p-1",
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
        dcc.Store(id="file-store"),  # Store to keep the file contents
    ],
    className="p-5 ml-5 mr-5",
)


# ------------------ Tabs ------------------ #
# dropdown menu items
initial_block_id = str(uuid.uuid4())
gm_input_group = html.Div(
    [
        dcc.Store(id="blocks-id", data=[initial_block_id]),  # Start with one block
        html.Div(
            id="blocks-container",
            children=[
                dmc.Grid(
                    id={"type": "gm-block", "index": initial_block_id},  # Start with one block
                    children=[
                        dmc.GridCol(
                            dbc.Button(
                                [html.I(className="fas fa-plus")],
                                id={"type": "gm-add-button", "index": initial_block_id},
                                className="btn-primary",
                            ),
                            span=1,
                        ),
                        dmc.GridCol(
                            dcc.Dropdown(
                                options=GM_DROPDOWN_MENU_OPTIONS,
                                value="GCF_ID",
                                id={"type": "gm-dropdown-menu", "index": initial_block_id},
                                clearable=False,
                            ),
                            span=6,
                        ),
                        dmc.GridCol(
                            [
                                dmc.TextInput(
                                    id={
                                        "type": "gm-dropdown-ids-text-input",
                                        "index": initial_block_id,
                                    },
                                    placeholder=GM_TEXT_INPUT_IDS_PLACEHOLDER,
                                    className="custom-textinput",
                                ),
                                dcc.Dropdown(
                                    id={
                                        "type": "gm-dropdown-bgc-class-dropdown",
                                        "index": initial_block_id,
                                    },
                                    options=GM_DROPDOWN_BGC_CLASS_OPTIONS,
                                    placeholder=GM_DROPDOWN_BGC_CLASS_PLACEHOLDER,
                                    multi=True,
                                    style={"display": "none"},
                                ),
                            ],
                            span=5,
                        ),
                    ],
                    gutter="md",
                )
            ],
        ),
    ]
)
# gm accordion (filter) card
gm_accordion = dmc.Accordion(
    [
        dmc.AccordionItem(
            [
                dmc.AccordionControl(
                    "Genomics filter",
                    disabled=True,
                    id="gm-accordion-control",
                    className="mt-5 mb-3",
                ),
                dmc.AccordionPanel(gm_input_group),
            ],
            value="gm-accordion",
        ),
    ],
    className="mt-5 mb-3",
)
# gm tab content
gm_content = dbc.Row(dbc.Col(gm_accordion, width=10, className="mx-auto"))
# mg tab content
mg_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div(id="file-content-mg")]),
        )
    ),
)
# tabs
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


def create_layout():  # noqa: D103
    return dmc.MantineProvider(
        [dbc.Container([navbar, uploader, tabs], fluid=True, className="p-0 dbc")]
    )
