import json
import uuid
from pathlib import Path
from unittest.mock import patch
import dash
import dash_mantine_components as dmc
import pandas as pd
import pytest
from dash_uploader import UploadStatus
from app.callbacks import disable_tabs_and_reset_blocks
from app.callbacks import gm_filter_add_block
from app.callbacks import gm_filter_apply
from app.callbacks import gm_scoring_apply
from app.callbacks import gm_table_select_rows
from app.callbacks import gm_table_toggle_selection
from app.callbacks import gm_table_update_datatable
from app.callbacks import process_uploaded_data
from app.callbacks import upload_data
from . import DATA_DIR


MOCK_FILE_PATH = DATA_DIR / "mock_obj_data.pkl"


@pytest.fixture
def mock_uuid(monkeypatch):
    def mock_uuid4():
        return "test-uuid"

    monkeypatch.setattr(uuid, "uuid4", mock_uuid4)


@pytest.fixture
def processed_data():
    # Use the actual process_uploaded_data function to get the processed data
    return process_uploaded_data(MOCK_FILE_PATH)


@pytest.fixture
def sample_processed_data():
    data = {
        "gcf_data": [
            {
                "GCF ID": "GCF_1",
                "# BGCs": 3,
                "BGC Classes": ["NRPS", "PKS"],
                "BGC IDs": ["BGC_1", "BGC_2", "BGC_3"],
                "BGC smiles": ["CCO", "CCN", "N/A"],
                "strains": ["Strain_1", "Strain_2", "Strain_3"],
            },
            {
                "GCF ID": "GCF_2",
                "# BGCs": 2,
                "BGC Classes": ["RiPP", "Terpene"],
                "BGC IDs": ["BGC_1", "BGC_3"],
                "BGC smiles": ["CCO", "N/A"],
                "strains": ["Strain_3"],
            },
        ]
    }
    return json.dumps(data)


def test_upload_data():
    # Create an UploadStatus object
    status = UploadStatus(
        uploaded_files=[MOCK_FILE_PATH], n_total=1, uploaded_size_mb=5.39, total_size_mb=5.39
    )
    upload_string, path_string = upload_data(status)

    # Check the result
    assert upload_string == f"Successfully uploaded: {MOCK_FILE_PATH.name} [5.39 MB]"
    assert path_string == str(MOCK_FILE_PATH)


@pytest.mark.parametrize("input_path", [None, Path("non_existent_file.pkl")])
def test_process_uploaded_data_invalid_input(input_path):
    processed_data, processed_links = process_uploaded_data(input_path)
    assert processed_data is None
    assert processed_links is None


def test_process_uploaded_data_structure():
    processed_data, processed_links = process_uploaded_data(MOCK_FILE_PATH)

    assert processed_data is not None
    assert processed_links is not None

    processed_data = json.loads(processed_data)
    processed_links = json.loads(processed_links)

    # Check overall structure
    assert isinstance(processed_data, dict)
    assert "n_bgcs" in processed_data
    assert "gcf_data" in processed_data

    # Add more specific assertions based on the expected content of your mock_obj_data.pkl
    assert len(processed_data["gcf_data"]) > 0
    assert len(processed_data["n_bgcs"]) > 0
    first_gcf = processed_data["gcf_data"][0]
    assert "GCF ID" in first_gcf
    assert "# BGCs" in first_gcf
    assert "BGC Classes" in first_gcf

    # Check n_bgcs structure
    assert isinstance(processed_data["n_bgcs"], dict)
    for key, value in processed_data["n_bgcs"].items():
        assert isinstance(key, str)  # Keys should be strings (JSON converts int to str)
        assert isinstance(value, list)

    # Check gcf_data structure
    assert isinstance(processed_data["gcf_data"], list)
    for gcf in processed_data["gcf_data"]:
        assert isinstance(gcf, dict)
        assert "GCF ID" in gcf
        assert "# BGCs" in gcf
        assert "BGC Classes" in gcf
        assert isinstance(gcf["GCF ID"], str)
        assert isinstance(gcf["# BGCs"], int)
        assert isinstance(gcf["BGC Classes"], list)

    # Check processed_links structure
    expected_link_keys = [
        "gcf_id",
        "spectrum_id",
        "strains",
        "method",
        "score",
        "cutoff",
        "standardised",
    ]
    for key in expected_link_keys:
        assert key in processed_links, f"Missing key '{key}' in processed links"
        assert isinstance(processed_links[key], list), f"{key} should be a list"

    # Check that all lists have the same length
    list_lengths = [len(processed_links[key]) for key in expected_link_keys]
    assert all(
        length == list_lengths[0] for length in list_lengths
    ), "Link data lists have inconsistent lengths"


def test_disable_tabs(mock_uuid):
    # Test with None as input
    result = disable_tabs_and_reset_blocks(None)
    assert result == (True, True, [], [], True, [], [], {}, {"display": "block"}, True)

    # Test with a string as input
    result = disable_tabs_and_reset_blocks(MOCK_FILE_PATH)

    # Unpack the result for easier assertion
    (
        gm_tab_disabled,
        gm_filter_accordion_disabled,
        gm_filter_block_ids,
        gm_filter_blocks,
        gm_scoring_accordion_disabled,
        gm_scoring_block_ids,
        gm_scoring_blocks,
        table_header_style,
        table_body_style,
        mg_tab_disabled,
    ) = result

    assert gm_tab_disabled is False
    assert gm_filter_accordion_disabled is False
    assert gm_scoring_accordion_disabled is False
    assert table_header_style == {}
    assert table_body_style == {"display": "block"}
    assert mg_tab_disabled is False
    assert gm_filter_block_ids == ["test-uuid"]
    assert len(gm_filter_blocks) == 1
    assert isinstance(gm_filter_blocks[0], dmc.Grid)
    assert gm_scoring_block_ids == ["test-uuid"]
    assert len(gm_scoring_blocks) == 1
    assert isinstance(gm_scoring_blocks[0], dmc.Grid)


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
def test_gm_filter_add_block(mock_uuid, n_clicks, initial_blocks, expected_result):
    if isinstance(expected_result, list):
        result = gm_filter_add_block(n_clicks, initial_blocks)
        assert result == expected_result
    else:
        with expected_result:
            gm_filter_add_block(n_clicks, initial_blocks)


def test_gm_filter_apply(sample_processed_data):
    data = json.loads(sample_processed_data)
    df = pd.DataFrame(data["gcf_data"])

    # Test GCF_ID filter
    gcf_ids = df["GCF ID"].iloc[:2].tolist()
    filtered_df = gm_filter_apply(df, ["GCF_ID"], [",".join(gcf_ids)], [[]])
    assert len(filtered_df) == 2
    assert set(filtered_df["GCF ID"]) == set(gcf_ids)

    # Test BGC_CLASS filter
    bgc_class = df["BGC Classes"].iloc[0][0]  # Get the first BGC class from the first row
    filtered_df = gm_filter_apply(df, ["BGC_CLASS"], [""], [[bgc_class]])
    assert len(filtered_df) > 0
    assert all(bgc_class in classes for classes in filtered_df["BGC Classes"])

    # Test no filter
    filtered_df = gm_filter_apply(df, [], [], [])
    assert len(filtered_df) == len(df)


def test_gm_table_update_datatable(sample_processed_data):
    with patch("app.callbacks.ctx") as mock_ctx:
        # Test with processed data and no filters applied
        mock_ctx.triggered_id = None
        result = gm_table_update_datatable(
            sample_processed_data,
            None,  # n_clicks
            [],  # dropdown_menus
            [],  # text_inputs
            [],  # bgc_class_dropdowns
            None,  # checkbox_value
        )

        assert len(result) == 6
        data, columns, tooltip_data, style, selected_rows, checkbox_value = result

        # Check data
        assert len(data) == 2
        assert data[0]["GCF ID"] == "GCF_1"
        assert data[1]["GCF ID"] == "GCF_2"

        # Check columns
        assert len(columns) == 2
        assert columns[0]["name"] == "GCF ID"
        assert columns[1]["name"] == "# BGCs"

        # Check style
        assert style == {"display": "block"}

        # Check selected_rows
        assert selected_rows == []

        # Check checkbox_value
        assert checkbox_value == []

        # Test with None input
        result = gm_table_update_datatable(None, None, [], [], [], None)
        assert result == ([], [], [], {"display": "none"}, [], [])

        # Test with apply-filters-button triggered
        mock_ctx.triggered_id = "gm-filter-apply-button"
        result = gm_table_update_datatable(
            sample_processed_data,
            1,  # n_clicks
            ["GCF_ID"],  # dropdown_menus
            ["GCF_1"],  # text_inputs
            [[]],  # bgc_class_dropdowns
            ["disabled"],  # checkbox_value
        )

        data, columns, tooltip_data, style, selected_rows, checkbox_value = result
        assert len(data) == 1
        assert data[0]["GCF ID"] == "GCF_1"
        assert checkbox_value == []


def test_gm_table_toggle_selection(sample_processed_data):
    data = json.loads(sample_processed_data)
    original_rows = data["gcf_data"]
    filtered_rows = original_rows[:2]

    # Test selecting all rows
    result = gm_table_toggle_selection(["disabled"], original_rows, filtered_rows)
    assert result == [0, 1]  # Assuming it now returns a list of indices directly

    # Test deselecting all rows
    result = gm_table_toggle_selection([], original_rows, filtered_rows)
    assert result == []

    # Test with None filtered_rows
    result = gm_table_toggle_selection(["disabled"], original_rows, None)
    assert result == list(range(len(original_rows)))  # Should select all rows in original_rows

    # Test with empty value (deselecting when no filter is applied)
    result = gm_table_toggle_selection([], original_rows, None)
    assert result == []


def test_gm_table_select_rows(sample_processed_data):
    data = json.loads(sample_processed_data)
    rows = data["gcf_data"]
    selected_rows = [0, 1]

    output1, output2 = gm_table_select_rows(rows, selected_rows)
    assert output1 == f"Total rows: {len(rows)}"
    assert output2.startswith(f"Selected rows: {len(selected_rows)}\nSelected GCF IDs: ")

    # Test with no rows
    output1, output2 = gm_table_select_rows([], None)
    assert output1 == "No data available."
    assert output2 == "No rows selected."


def test_gm_scoring_apply_metcalf_raw():
    """Test gm_scoring_apply with Metcalf method and raw scores."""
    # Create test DataFrame
    df = pd.DataFrame(
        {
            "method": ["metcalf", "metcalf", "other"],
            "standardised": [False, True, False],
            "cutoff": [1.5, 2.0, 1.0],
            "score": [2.0, 2.5, 1.5],
        }
    )

    # Test parameters
    dropdown_menus = ["METCALF"]
    radiobuttons = ["RAW"]
    cutoffs_met = ["1.0"]

    result = gm_scoring_apply(df, dropdown_menus, radiobuttons, cutoffs_met)

    assert len(result) == 1, "Should return one row"
    assert result.iloc[0]["method"] == "metcalf", "Method should be metcalf"
    assert not result.iloc[0]["standardised"], "Should be raw (not standardised)"
    assert result.iloc[0]["cutoff"] >= 1.0, "Cutoff should be >= 1.0"


def test_gm_scoring_apply_metcalf_standardised():
    """Test gm_scoring_apply with Metcalf method and standardised scores."""
    # Create test DataFrame
    df = pd.DataFrame(
        {
            "method": ["metcalf", "metcalf", "other"],
            "standardised": [False, True, False],
            "cutoff": [1.5, 2.0, 1.0],
            "score": [2.0, 2.5, 1.5],
        }
    )

    # Test parameters
    dropdown_menus = ["METCALF"]
    radiobuttons = ["STANDARDISED"]
    cutoffs_met = ["1.5"]

    result = gm_scoring_apply(df, dropdown_menus, radiobuttons, cutoffs_met)

    assert len(result) == 1, "Should return one row"
    assert result.iloc[0]["method"] == "metcalf", "Method should be metcalf"
    assert result.iloc[0]["standardised"], "Should be standardised"
    assert result.iloc[0]["cutoff"] >= 1.5, "Cutoff should be >= 1.5"


def test_gm_scoring_apply_empty_inputs():
    """Test gm_scoring_apply with empty inputs."""
    df = pd.DataFrame(
        {"method": ["metcalf"], "standardised": [False], "cutoff": [1.0], "score": [2.0]}
    )

    result = gm_scoring_apply(df, [], [], [])

    assert len(result) == 1, "Should return original DataFrame"
    assert result.equals(df), "Should return unmodified DataFrame"
