import os
from pathlib import Path
from dash_uploader import UploadStatus
from app.app import disable_tabs
from app.app import upload_data
from . import DATA_DIR


MOCK_FILE_PATH = Path(DATA_DIR, "mock_obj_data.pkl")


def test_upload_data():
    # Create an UploadStatus object
    status = UploadStatus(
        uploaded_files=[MOCK_FILE_PATH], n_total=1, uploaded_size_mb=5.39, total_size_mb=5.39
    )
    upload_string, path_string = upload_data(status)

    # Check the result
    assert upload_string == f"Successfully uploaded: {os.path.basename(MOCK_FILE_PATH)} [5.39 MB]"
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
