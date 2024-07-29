import uuid
import dash_bootstrap_components as dbc
import dash_uploader as du
from dash import dcc
from dash import html


# Define the navigation bar
def create_navbar():
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
                    dbc.NavItem(
                        dbc.NavLink("Doc", href="https://nplinker.github.io/nplinker/latest/")
                    ),
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
    return navbar


# Define the file uploader
def create_uplader():
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
                    html.Div(
                        children="No file uploaded", id="dash-uploader-output", className="p-4"
                    ),
                    className="d-flex justify-content-center",
                )
            ),
            dcc.Store(id="file-store"),  # Store to keep the file contents
        ],
        className="p-5 ml-5 mr-5",
    )
    return uploader


# Define the tabs
def create_tabs():
    # gm tab content
    gm_content = dbc.Row(
        dbc.Col(
            dbc.Card(
                dbc.CardBody([html.Div(id="file-content-gm")]),
            )
        )
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
                        className="disabled-tab",
                    ),
                    dbc.Tab(
                        mg_content,
                        label="Metabolomics -> Genomics",
                        activeTabClassName="fw-bold",
                        disabled=True,
                        id="mg-tab",
                        className="disabled-tab",
                    ),
                ],
            ),
        ),
        className="p-5",
    )
    return tabs


def create_layout():
    return dbc.Container(
        [create_navbar(), create_uplader(), create_tabs()], fluid=True, className="p-0"
    )
