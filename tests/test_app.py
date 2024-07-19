from contextvars import copy_context
from dash._callback_context import context_value
from dash._utils import AttributeDict

# Import the names of callback functions you want to test
from app.app import upload_data


TEST_DATA = "/Users/giuliacrocioni/Desktop/docs/eScience/projects/NPLinker/nplinker-webapp/nplinker_quickstart/output/npl.pkl"
def test_update_callback():
    output = upload_data(1, 0)
    assert output == "button 1: 1 & button 2: 0"


def test_display_callback():
    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "btn-1-ctx-example.n_clicks"}]})
        )
        return display(1, 0, 0)

    ctx = copy_context()
    output = ctx.run(run_callback)
    assert output == "You last clicked button with ID btn-1-ctx-example"
