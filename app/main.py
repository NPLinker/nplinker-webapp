from app import app
from app import create_layout


app.layout = create_layout()

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
