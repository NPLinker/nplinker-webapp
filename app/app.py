from callbacks import app
from layouts import create_layout


# ------------------ App Layout ------------------ #
app.layout = create_layout()

if __name__ == "__main__":
    app.run_server(debug=True)
