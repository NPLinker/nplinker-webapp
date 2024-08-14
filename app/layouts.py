import uuid
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
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
        dcc.Store(id="blocks-id", data=[]),  # Start with one block
        html.Div(
            id="blocks-container",
            children=[],
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
# gm graph
gm_graph = dcc.Graph(id="gm-graph", className="mt-5 mb-3", style={"display": "none"})
# gm tab content
gm_content = dbc.Row(
    [
        dbc.Col(gm_accordion, width=10, className="mx-auto"),
        dbc.Col(gm_graph, width=10, className="mx-auto"),
    ]
)
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
