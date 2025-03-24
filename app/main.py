from callbacks import app
from layouts import create_layout


app.layout = create_layout()

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
