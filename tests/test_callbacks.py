from contextvars import copy_context
import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict
from dash_uploader import UploadStatus
from app.callbacks import disable_tabs
from app.callbacks import gm_filter
from app.callbacks import upload_data
from . import DATA_DIR


MOCK_FILE_PATH = DATA_DIR / "mock_obj_data.pkl"


def test_upload_data():
    # Create an UploadStatus object
    status = UploadStatus(
        uploaded_files=[MOCK_FILE_PATH], n_total=1, uploaded_size_mb=5.39, total_size_mb=5.39
    )
    upload_string, path_string = upload_data(status)

    # Check the result
    assert upload_string == f"Successfully uploaded: {MOCK_FILE_PATH.name} [5.39 MB]"
    assert path_string == str(MOCK_FILE_PATH)


def test_disable_tabs():
    # Test with None as input
    result = disable_tabs(None)
    assert result[0] is True  # GM tab should be disabled
    assert result[1] is True  # MG tab should be disabled

    # Test with a string as input
    result = disable_tabs(MOCK_FILE_PATH)
    assert result[0] is False  # GM tab should be enabled
    assert result[1] is False  # MG tab should be enabled


@pytest.mark.parametrize(
    "gcf_ids, gcf_bigscape, triggered_prop_id, expected_result",
    [
        (
            "10, 34, 56",
            "",
            "gcf-ids-dropdown-input.value",
            ("10, 34, 56", ""),
        ),  # gcf-ids-dropdown-input triggered
        (
            "",
            "class1",
            "gcf-bigscape-dropdown-input.value",
            ("", "class1"),
        ),  # gcf-bigscape-dropdown-input triggered
        (
            "10, 34, 56",
            "class1",
            "gcf-ids-dropdown-clear.n_clicks",
            ("", "class1"),
        ),  # gcf-ids-dropdown-clear triggered
        (
            "10, 34, 56",
            "class1",
            "gcf-bigscape-dropdown-clear.n_clicks",
            ("10, 34, 56", ""),
        ),  # gcf-bigscape-dropdown-clear triggered
        ("", "", "no_triggering_context", ("", "")),  # No triggering context
    ],
)
def test_gm_filter(gcf_ids, gcf_bigscape, triggered_prop_id, expected_result):
    def run_callback():
        gcf_ids_clear = None
        gcf_bigscape_clear = None
        if triggered_prop_id == "no_triggering_context":
            context_value.set(AttributeDict(**{"triggered_inputs": []}))
        else:
            context_value.set(
                AttributeDict(**{"triggered_inputs": [{"prop_id": triggered_prop_id}]})
            )
        return gm_filter(gcf_ids, gcf_ids_clear, gcf_bigscape, gcf_bigscape_clear)

    ctx = copy_context()
    output = ctx.run(run_callback)
    assert output == expected_result
