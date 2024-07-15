import tempfile
import dash_bootstrap_components as dbc
import dash_uploader as du
from dash import Dash
from dash import Input
from dash import Output
from dash import clientside_callback
from dash import html
from flask import Flask
from flask import jsonify
from flask import request


UPLOAD_FOLDER = "uploads"  # Folder where uploaded files will be stored
server = Flask(__name__)
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.UNITED, dbc_css, dbc.icons.FONT_AWESOME],
)

src = app.get_asset_url("uploadform.html")
STATUS_FAILED = "failed"
STATUS_SUCCESS = "success"

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

# Define the navigation bar
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
            brand_href="https://github.com/NPLinker/nplinker-webapp",
            color="primary",
            className="p-3 mb-2",
            dark=True,
        ),
    ),
)

# ------------------ Uploader ------------------ #
# Configure the upload folder
TEMP_DIR = tempfile.mkdtemp()
du.configure_upload(app, TEMP_DIR)


# ------------------ Tabs ------------------ #
# gm tab content
gm_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div(children="No file uploaded", id="dash-uploader-output")]),
        )
    )
)
# mg tab content
mg_content = dbc.Row(
    dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div(children="No file uploaded")]),
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
                ),
                dbc.Tab(
                    mg_content,
                    label="Metabolomics -> Genomics",
                    activeTabClassName="fw-bold",
                ),
            ],
        ),
    ),
    className="p-5",
)

uploader_flask = html.Iframe(src=src)

app.layout = dbc.Container([navbar, uploader_flask, tabs], fluid=True, className="p-0")

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

# TODO: Verify if this is the correct way to handle file upload
# @server.route("/upload", methods=["POST"])
# def upload_file():
#     try:
#         file_chunk_size = 1024 * 1024  # 1 MB chunk size
#         file_path = None

#         # Ensure the uploads folder exists
#         os.makedirs(server.config["UPLOAD_FOLDER"], exist_ok=True)

#         # Retrieve the uploaded file from the request
#         if "file" not in request.files:
#             return jsonify({"error": "No file part in the request."}), 400

#         uploaded_file = request.files["file"]

#         # Save the uploaded file to disk
#         file_path = os.path.join(server.config["UPLOAD_FOLDER"], uploaded_file.filename)
#         print(file_path)
#         with open(file_path, "wb") as f:
#             while True:
#                 chunk = uploaded_file.stream.read(file_chunk_size)
#                 if not chunk:
#                     break
#                 f.write(chunk)
#         file = request.files["file"]
#         file.save(file_path)
#         with open(file_path, "rb") as f:
#             decoded_data = base64.b64decode(f.read())
#             try:
#                 decoded_text = decoded_data.decode("utf-8")
#             except Exception as e:
#                 print(e)
#             print(len(decoded_data))
#             print(decoded_data)
#         with open(file_path, "rb") as f:
#             file_content = f.read()
#             print(type(file_content))
#         decoded_content = base64.b64decode(file_content)
#         print(type(decoded_content))
#         try:
#             data = pickle.loads(io.BytesIO(decoded_content))
#         except Exception as e:
#             print(e)
#         return jsonify({"file_path": file_path}), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@server.route("/upload", methods=["POST"])
def upload_file():
    # check if the post request has the file part
    print(request.values)
    # print(type(request.values))
    # print(len(request.values))
    # print(request.files)
    # print(type(request.files))
    # print(request.files["file"])

    return jsonify(status=STATUS_SUCCESS)


# TODO: add callback to handle file upload
# @app.callback(
#     Output("output-data-upload", "children"),
#     [Input("upload-data", "contents")],
#     [State("upload-data", "filename"), State("upload-data", "last_modified")],
# )
# def update_output(contents, filename, last_modified):
#     if contents is not None:
#         try:
#             # Perform upload via Flask route /upload
#             upload_response = requests.post(
#                 "http://127.0.0.1:8050/upload",  # Update with your server address
#                 files={"file": (filename, contents.encode())},
#             )
#             if upload_response.status_code == 200:
#                 file_path = upload_response.json()["file_path"]
#                 # Read and process the uploaded file
#                 with open(file_path, "rb") as f:
#                     # print(type(f))
#                     # file_content = f.read()
#                     # print(type(file_content))
#                     # # Example: Read data from pickle file
#                     # # _, content_string = contents.split(",")
#                     # decoded = base64.b64decode(file_content)
#                     # type(dec)
#                     # # if filename.endswith(".pkl"):
#                     # data = pickle.load(io.BytesIO(decoded))
#                     # data = pickle.load(f)
#                     # return html.Div([html.H5(f"File selected: {filename}"), html.P(f"File contents: {data}")])
#                     return html.Div(
#                         [html.H5(f"File uploaded: {filename}"), html.P(f"File path: {file_path}")]
#                     )
#             else:
#                 return html.Div(["Error uploading file."])

#         except Exception as e:
#             return html.Div([f"Error: {e}"])

#     else:
#         return html.Div(["No file selected"])

# TODO: add tests

if __name__ == "__main__":
    app.run_server(debug=True)
