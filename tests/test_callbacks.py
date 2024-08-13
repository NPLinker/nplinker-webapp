import uuid
import dash
import pytest
from dash_uploader import UploadStatus
from app.callbacks import add_block
from app.callbacks import disable_tabs_and_reset_blocks
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
    result = disable_tabs_and_reset_blocks(None)
    assert result[0] is True  # GM tab should be disabled
    assert result[1] is True  # GM accordion should be disabled
    assert result[2] is True  # MG tab should be disabled
    assert result[3] == []  # No blocks should be displayed
    assert result[4] == []  # No blocks should be displayed

    # Test with a string as input
    result = disable_tabs_and_reset_blocks(MOCK_FILE_PATH)
    assert result[0] is False  # GM tab should be enabled
    assert result[1] is False  # GM accordion should be enabled
    assert result[2] is False  # MG tab should be enabled
    assert len(result[3]) == 1  # One block should be displayed
    assert len(result[4]) == 1  # One block should be displayed


@pytest.fixture
def mock_uuid(monkeypatch):
    def mock_uuid4():
        return "test-uuid"

    monkeypatch.setattr(uuid, "uuid4", mock_uuid4)


@pytest.mark.parametrize(
    "n_clicks, initial_blocks, expected_result",
    [
        ([], ["block1"], pytest.raises(dash.exceptions.PreventUpdate)),  # no buttons clicked
        ([1], ["block1", "block2"], ["block1", "block2", "test-uuid"]),  # one button clicked once
        (
            [1, 1, 1],
            ["block1", "block2"],
            ["block1", "block2", "test-uuid"],
        ),  # three buttons, each clicked once
    ],
)
def test_add_block(mock_uuid, n_clicks, initial_blocks, expected_result):
    if isinstance(expected_result, list):
        result = add_block(n_clicks, initial_blocks)
        assert result == expected_result
    else:
        with expected_result:
            add_block(n_clicks, initial_blocks)
