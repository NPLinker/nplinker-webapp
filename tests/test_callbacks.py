import uuid
import dash
import dash_mantine_components as dmc
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


@pytest.fixture
def mock_uuid(monkeypatch):
    def mock_uuid4():
        return "test-uuid"

    monkeypatch.setattr(uuid, "uuid4", mock_uuid4)


def test_disable_tabs(mock_uuid):
    # Test with None as input
    result = disable_tabs_and_reset_blocks(None)
    assert result == (True, True, {}, {"display": "block"}, True, [], [])

    # Test with a string as input
    result = disable_tabs_and_reset_blocks(MOCK_FILE_PATH)

    # Unpack the result for easier assertion
    (
        gm_tab_disabled,
        gm_accordion_disabled,
        table_header_style,
        table_body_style,
        mg_tab_disabled,
        block_ids,
        blocks,
    ) = result

    assert gm_tab_disabled is False
    assert gm_accordion_disabled is False
    assert table_header_style == {}
    assert table_body_style == {"display": "block"}
    assert mg_tab_disabled is False
    assert block_ids == ["test-uuid"]
    assert len(blocks) == 1
    assert isinstance(blocks[0], dmc.Grid)


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
