import os
import sys
from callbacks import app
from layouts import create_layout


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


app.layout = create_layout()

if __name__ == "__main__":
    app.run_server(debug=True)
