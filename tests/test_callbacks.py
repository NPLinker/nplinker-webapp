import json
import pickle
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
from app.callbacks import gm_generate_excel
from app.callbacks import gm_table_select_rows
from app.callbacks import gm_table_toggle_selection
from app.callbacks import gm_table_update_datatable
from app.callbacks import gm_toggle_download_button
from app.callbacks import load_demo_data
from app.callbacks import mg_filter_add_block
from app.callbacks import mg_filter_apply
from app.callbacks import mg_generate_excel
from app.callbacks import mg_table_select_rows
from app.callbacks import mg_table_toggle_selection
from app.callbacks import mg_table_update_datatable
from app.callbacks import process_uploaded_data
from app.callbacks import scoring_apply
from app.callbacks import upload_data
from app.config import GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from app.config import MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
from . import DATA_DIR


MOCK_FILE_PATH = DATA_DIR / "mock_obj_data.pkl"
MOCK_FILE_PATH_NO_LINKS = DATA_DIR / "mock_obj_data_no_links.pkl"


@pytest.fixture
def mock_uuid(monkeypatch):
    def mock_uuid4():
        return "test-uuid"

    monkeypatch.setattr(uuid, "uuid4", mock_uuid4)


@pytest.fixture
def processed_data():
    # Use the actual process_uploaded_data function to get the processed data
    return process_uploaded_data(MOCK_FILE_PATH, cleanup=False)


@pytest.fixture
def sample_processed_data():
    data = {
        "gcf_data": [
            {
                "GCF ID": "GCF_1",
                "# BGCs": 3,
                "BGC Classes": [
                    ["NRPS"],
                    ["PKS"],
                    ["NRPS"],
                ],
                "BGC IDs": ["BGC_1", "BGC_2", "BGC_3"],
                "strains": ["Strain_1", "Strain_2", "Strain_3"],
            },
            {
                "GCF ID": "GCF_2",
                "# BGCs": 2,
                "BGC Classes": [["RiPP"], ["Terpene"]],
                "BGC IDs": ["BGC_1", "BGC_3"],
                "strains": ["Strain_3"],
            },
        ],
        "mf_data": [
            {
                "MF ID": "MF_1",
                "# Spectra": 2,
                "Spectra IDs": ["Spec_1", "Spec_2"],
                "Spectra precursor m/z": [150.5, 220.3],
                "Spectra GNPS IDs": ["GNPS_1", "GNPS_2"],
                "strains": ["Strain_1", "Strain_2"],
            },
            {
                "MF ID": "MF_2",
                "# Spectra": 3,
                "Spectra IDs": ["Spec_3", "Spec_4", "Spec_5"],
                "Spectra precursor m/z": [180.1, 210.7, 230.2],
                "Spectra GNPS IDs": ["GNPS_3", "GNPS_4", "GNPS_5"],
                "strains": ["Strain_2", "Strain_3"],
            },
        ],
    }
    return json.dumps(data)


def test_upload_data():
    # Create an UploadStatus object
    status = UploadStatus(
        uploaded_files=[MOCK_FILE_PATH], n_total=1, uploaded_size_mb=5.39, total_size_mb=5.39
    )
    upload_string, path_string, _ = upload_data(status)

    # Check the result
    assert upload_string == f"Successfully uploaded: {MOCK_FILE_PATH.name} [5.39 MB]"
    assert path_string == str(MOCK_FILE_PATH)


def test_load_demo_data():
    """Test the load_demo_data callback function."""

    # Test with no clicks - should prevent update
    with pytest.raises(dash.exceptions.PreventUpdate):
        load_demo_data(None)

    # Test with actual click - should load demo data
    result = load_demo_data(1)
    message, file_path, spinner = result

    # Check that the function returns expected format
    assert isinstance(message, str)
    assert isinstance(file_path, (str, type(None)))
    assert spinner is None

    # If successful, should contain success message and valid file path
    if file_path is not None:
        assert "Successfully loaded demo data" in message
        assert "demo_data_" in file_path
        # Verify the file actually exists and is valid
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        assert data is not None
    else:
        # If failed, should contain error message
        assert "Error" in message


@pytest.mark.parametrize("input_path", [None, Path("non_existent_file.pkl")])
def test_process_uploaded_data_invalid_input(input_path):
    processed_data, processed_links, _ = process_uploaded_data(input_path, cleanup=False)
    assert processed_data is None
    assert processed_links is None


def test_process_uploaded_data_structure():
    processed_data, processed_links, _ = process_uploaded_data(MOCK_FILE_PATH, cleanup=False)
    processed_data_no_links, processed_links_no_links, _ = process_uploaded_data(
        MOCK_FILE_PATH_NO_LINKS, cleanup=False
    )

    assert processed_data is not None
    assert processed_links is not None
    assert processed_data_no_links == processed_data
    assert len(json.loads(processed_links_no_links)) == 0  # type: ignore

    processed_data = json.loads(processed_data)
    processed_links = json.loads(processed_links)

    # Check overall structure
    assert isinstance(processed_data, dict)
    assert "n_bgcs" in processed_data
    assert "gcf_data" in processed_data
    assert "mf_data" in processed_data

    # Add more specific assertions based on the expected content of your mock_obj_data.pkl
    assert len(processed_data["n_bgcs"]) > 0
    assert len(processed_data["gcf_data"]) > 0
    assert len(processed_data["mf_data"]) > 0

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
        # Verify nested list structure for BGC Classes
        for bgc_class in gcf["BGC Classes"]:
            assert isinstance(bgc_class, list)
            for cls in bgc_class:
                assert isinstance(cls, str)

    # Check mf_data structure
    assert isinstance(processed_data["mf_data"], list)
    for mf in processed_data["mf_data"]:
        assert isinstance(mf, dict)
        assert "MF ID" in mf
        assert "# Spectra" in mf
        assert "Spectra IDs" in mf
        assert isinstance(mf["MF ID"], str)
        assert isinstance(mf["# Spectra"], int)
        assert isinstance(mf["Spectra IDs"], list)
        assert isinstance(mf["Spectra precursor m/z"], list)
        assert isinstance(mf["Spectra GNPS IDs"], list)
        assert isinstance(mf["strains"], list)

    # Check processed_links structure
    assert isinstance(processed_links, dict)
    assert "gm_data" in processed_links
    assert "mg_data" in processed_links

    # Check gm_data structure
    assert isinstance(processed_links["gm_data"], dict)
    expected_gm_keys = [
        "gcf_id",
        "spectrum",
        "method",
        "score",
        "cutoff",
        "standardised",
    ]
    for key in expected_gm_keys:
        assert key in processed_links["gm_data"], f"Missing key '{key}' in gm_data"
        assert isinstance(processed_links["gm_data"][key], list), f"gm_data[{key}] should be a list"

    # Check that all gm_data lists have the same length
    gm_list_lengths = [len(processed_links["gm_data"][key]) for key in expected_gm_keys]
    assert all(length == gm_list_lengths[0] for length in gm_list_lengths), (
        "GM link data lists have inconsistent lengths"
    )

    # Check spectrum structure in gm_data
    if gm_list_lengths[0] > 0:  # Only if there are any GM links
        for spectrum in processed_links["gm_data"]["spectrum"]:
            assert isinstance(spectrum, dict)
            assert "id" in spectrum
            assert "precursor_mz" in spectrum
            assert "gnps_id" in spectrum
            assert "mf_id" in spectrum
            assert "strains" in spectrum
            assert isinstance(spectrum["strains"], list)

    # Check mg_data structure
    assert isinstance(processed_links["mg_data"], dict)
    expected_mg_keys = [
        "mf_id",
        "gcf",
        "method",
        "score",
        "cutoff",
        "standardised",
    ]
    for key in expected_mg_keys:
        assert key in processed_links["mg_data"], f"Missing key '{key}' in mg_data"
        assert isinstance(processed_links["mg_data"][key], list), f"mg_data[{key}] should be a list"

    # Check that all mg_data lists have the same length
    mg_list_lengths = [len(processed_links["mg_data"][key]) for key in expected_mg_keys]
    assert all(length == mg_list_lengths[0] for length in mg_list_lengths), (
        "MG link data lists have inconsistent lengths"
    )

    # Check gcf structure in mg_data
    if mg_list_lengths[0] > 0:  # Only if there are any MG links
        for gcf in processed_links["mg_data"]["gcf"]:
            assert isinstance(gcf, dict)
            assert "id" in gcf
            assert "# BGCs" in gcf
            assert "BGC IDs" in gcf
            assert "BGC Classes" in gcf
            assert "strains" in gcf
            assert isinstance(gcf["strains"], list)
            assert isinstance(gcf["BGC IDs"], list)
            assert isinstance(gcf["BGC Classes"], list)


def test_process_uploaded_data_cleanup(tmp_path):
    """Ensure that temporary file is deleted when cleanup=True."""
    temp_file = tmp_path / "temp_data.pkl"

    dummy_data = (None, [], None, [], None, None)
    with open(temp_file, "wb") as f:
        pickle.dump(dummy_data, f)

    # Confirm file exists
    assert temp_file.exists()

    # Call the function with cleanup=True (default)
    processed_data, _, _ = process_uploaded_data(temp_file, cleanup=True)

    # File should be deleted after processing
    assert not temp_file.exists()
    assert processed_data is not None  # Sanity check: function still processed the file


def test_disable_tabs(mock_uuid):
    default_gm_column_value = (
        [GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS[0]]
        if GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
        else []
    )
    default_mg_column_value = (
        [MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS[0]]
        if MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS
        else []
    )

    # Test with None as input
    result = disable_tabs_and_reset_blocks(None)
    assert result == (
        # GM tab - disabled
        True,
        True,
        [],
        [],
        {},
        {"display": "block"},
        True,
        [],
        [],
        True,
        [],
        [],
        [],
        [],
        default_gm_column_value,
        "n_bgcs",
        # MG tab - disabled
        True,
        True,
        [],
        [],
        {},
        {"display": "block"},
        True,
        [],
        [],
        True,
        [],
        [],
        [],
        [],
        default_mg_column_value,
    )

    # Test with a string as input
    result = disable_tabs_and_reset_blocks(MOCK_FILE_PATH)

    # Unpack the result for easier assertion
    (
        # GM tab outputs
        gm_tab_disabled,
        gm_filter_accordion_disabled,
        gm_filter_block_ids,
        gm_filter_blocks,
        gm_table_header_style,
        gm_table_body_style,
        gm_scoring_accordion_disabled,
        gm_scoring_block_ids,
        gm_scoring_blocks,
        gm_results_disabled,
        gm_table_selected_rows,
        gm_table_checkbox_value,
        gm_filter_accordion_value,
        gm_scoring_accordion_value,
        gm_results_table_column_toggle,
        gm_graph_dropdown,
        # MG tab outputs
        mg_tab_disabled,
        mg_filter_accordion_disabled,
        mg_filter_block_ids,
        mg_filter_blocks,
        mg_table_header_style,
        mg_table_body_style,
        mg_scoring_accordion_disabled,
        mg_scoring_block_ids,
        mg_scoring_blocks,
        mg_results_disabled,
        mg_table_selected_rows,
        mg_table_checkbox_value,
        mg_filter_accordion_value,
        mg_scoring_accordion_value,
        mg_results_table_column_toggle,
    ) = result

    # Assert GM tab outputs
    assert gm_tab_disabled is False
    assert gm_filter_accordion_disabled is False
    assert gm_filter_block_ids == ["test-uuid"]
    assert len(gm_filter_blocks) == 1
    assert isinstance(gm_filter_blocks[0], dmc.Grid)
    assert gm_table_header_style == {}
    assert gm_table_body_style == {"display": "block"}
    assert gm_scoring_accordion_disabled is False
    assert gm_scoring_block_ids == ["test-uuid"]
    assert len(gm_scoring_blocks) == 1
    assert isinstance(gm_scoring_blocks[0], dmc.Grid)
    assert gm_results_disabled is False
    assert gm_table_selected_rows == []
    assert gm_table_checkbox_value == []
    assert gm_filter_accordion_value == []
    assert gm_scoring_accordion_value == []
    assert gm_results_table_column_toggle == default_gm_column_value
    assert gm_graph_dropdown == "n_bgcs"

    # Assert MG tab outputs
    assert mg_tab_disabled is False
    assert mg_filter_accordion_disabled is False
    assert mg_filter_block_ids == ["test-uuid"]
    assert len(mg_filter_blocks) == 1
    assert isinstance(mg_filter_blocks[0], dmc.Grid)
    assert mg_table_header_style == {}
    assert mg_table_body_style == {"display": "block"}
    assert mg_scoring_accordion_disabled is False
    assert mg_scoring_block_ids == ["test-uuid"]
    assert len(mg_scoring_blocks) == 1
    assert isinstance(mg_scoring_blocks[0], dmc.Grid)
    assert mg_results_disabled is False
    assert mg_table_selected_rows == []
    assert mg_table_checkbox_value == []
    assert mg_filter_accordion_value == []
    assert mg_scoring_accordion_value == []
    assert mg_results_table_column_toggle == default_mg_column_value


def test_scoring_apply_metcalf_raw():
    """Test scoring_apply with Metcalf method and raw scores."""
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

    result = scoring_apply(df, dropdown_menus, radiobuttons, cutoffs_met)

    assert len(result) == 1, "Should return one row"
    assert result.iloc[0]["method"] == "metcalf", "Method should be metcalf"
    assert not result.iloc[0]["standardised"], "Should be raw (not standardised)"
    assert result.iloc[0]["cutoff"] >= 1.0, "Cutoff should be >= 1.0"


def test_scoring_apply_metcalf_standardised():
    """Test scoring_apply with Metcalf method and standardised scores."""
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

    result = scoring_apply(df, dropdown_menus, radiobuttons, cutoffs_met)

    assert len(result) == 1, "Should return one row"
    assert result.iloc[0]["method"] == "metcalf", "Method should be metcalf"
    assert result.iloc[0]["standardised"], "Should be standardised"
    assert result.iloc[0]["cutoff"] >= 1.5, "Cutoff should be >= 1.5"


def test_scoring_apply_empty_inputs():
    """Test scoring_apply with empty inputs."""
    df = pd.DataFrame(
        {"method": ["metcalf"], "standardised": [False], "cutoff": [1.0], "score": [2.0]}
    )

    result = scoring_apply(df, [], [], [])

    assert len(result) == 1, "Should return original DataFrame"
    assert result.equals(df), "Should return unmodified DataFrame"


# ----------------- GM tab tests -----------------
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
    bgc_class = df["BGC Classes"].iloc[0][0][0]  # Get first class from nested structure
    filtered_df = gm_filter_apply(df, ["BGC_CLASS"], [""], [[bgc_class]])
    assert len(filtered_df) > 0
    assert any(
        bgc_class in [cls for sublist in classes for cls in sublist]
        for classes in filtered_df["BGC Classes"]
    )

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

        assert len(result) == 7
        data, columns, tooltip_data, style, selected_rows, checkbox_value, _ = result

        # Check data
        assert len(data) == 2
        assert data[0]["GCF ID"] == "GCF_1"
        assert data[1]["GCF ID"] == "GCF_2"

        # Check columns
        assert len(columns) == 4
        assert columns[0]["name"] == "GCF ID"
        assert columns[1]["name"] == "# BGCs"
        assert columns[2]["name"] == "BGC Classes"
        assert columns[3]["name"] == "MiBIG IDs"

        # Check style
        assert style == {"display": "block"}

        # Check selected_rows
        assert selected_rows == []

        # Check checkbox_value
        assert checkbox_value == []

        # Test with None input
        result = gm_table_update_datatable(None, None, [], [], [], None)
        assert result == ([], [], [], {"display": "none"}, [], [], None)

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

        data, columns, tooltip_data, style, selected_rows, checkbox_value, _ = result
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
    assert output2.startswith(f"Selected rows: {len(selected_rows)}\n")

    # Test with no rows
    output1, output2 = gm_table_select_rows([], None)
    assert output1 == "No data available."
    assert output2 == "No rows selected."


def test_gm_toggle_download_button():
    """Test the toggle_download_button function with different inputs."""
    # Test with empty table data - should disable the button
    result = gm_toggle_download_button([])
    assert result == (True, False, "")

    # Test with populated table data - should enable the button
    sample_data = [{"GCF ID": 1, "# Links": 5}]
    result = gm_toggle_download_button(sample_data)
    assert result == (False, False, "")


def test_gm_generate_excel_error_handling():
    """Test the generate_excel function error handling."""
    table_data = [{"GCF ID": 1, "spectrum_ids_str": "123"}]
    detailed_data = {"1": {"spectrum_ids": ["123"]}}

    with (
        patch("app.callbacks.ctx") as mock_ctx,
        patch("app.callbacks.pd.ExcelWriter") as mock_writer,
    ):
        mock_ctx.triggered = True
        # Simulate an error during Excel generation
        mock_writer.side_effect = Exception("Excel write error")

        result = gm_generate_excel(1, table_data, detailed_data)

        # Should return an error message
        assert result[0] is None
        assert result[1] is True  # Alert is open
        assert "Error generating Excel file" in result[2]


# ----------------- MG tab tests -----------------
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
def test_mg_filter_add_block(mock_uuid, n_clicks, initial_blocks, expected_result):
    if isinstance(expected_result, list):
        result = mg_filter_add_block(n_clicks, initial_blocks)
        assert result == expected_result
    else:
        with expected_result:
            mg_filter_add_block(n_clicks, initial_blocks)


def test_mg_filter_apply(sample_processed_data):
    data = json.loads(sample_processed_data)
    df = pd.DataFrame(data["mf_data"])

    # Test MF_ID filter
    mf_ids = df["MF ID"].iloc[:1].tolist()
    filtered_df = mg_filter_apply(df, ["MF_ID"], [",".join(mf_ids)], [""])
    assert len(filtered_df) == 1
    assert set(filtered_df["MF ID"]) == set(mf_ids)

    # Test SPECTRUM_ID filter
    spec_id = df["Spectra IDs"].iloc[0][0]  # Get first spectrum ID from first row
    filtered_df = mg_filter_apply(df, ["SPECTRUM_ID"], [""], [spec_id])
    assert len(filtered_df) == 1
    assert spec_id in filtered_df.iloc[0]["Spectra IDs"]

    # Test no filter
    filtered_df = mg_filter_apply(df, [], [], [])
    assert len(filtered_df) == len(df)


def test_mg_table_update_datatable(sample_processed_data):
    with patch("app.callbacks.ctx") as mock_ctx:
        # Test with processed data and no filters applied
        mock_ctx.triggered_id = None
        result = mg_table_update_datatable(
            sample_processed_data,
            None,  # n_clicks
            [],  # dropdown_menus
            [],  # mf_text_inputs
            [],  # spec_text_inputs
            None,  # checkbox_value
        )

        assert len(result) == 7
        data, columns, tooltip_data, style, selected_rows, checkbox_value, _ = result

        # Check data
        assert len(data) == 2
        assert data[0]["MF ID"] == "MF_1"
        assert data[1]["MF ID"] == "MF_2"

        # Check columns
        assert len(columns) == 3
        assert columns[0]["name"] == "MF ID"
        assert columns[1]["name"] == "# Spectra"
        assert columns[2]["name"] == "Spectra GNPS IDs"

        # Check style
        assert style == {"display": "block"}

        # Check selected_rows
        assert selected_rows == []

        # Check checkbox_value
        assert checkbox_value == []

        # Test with None input
        result = mg_table_update_datatable(None, None, [], [], [], None)
        assert result == ([], [], [], {"display": "none"}, [], [], None)

        # Test with apply-filters-button triggered
        mock_ctx.triggered_id = "mg-filter-apply-button"
        result = mg_table_update_datatable(
            sample_processed_data,
            1,  # n_clicks
            ["MF_ID"],  # dropdown_menus
            ["MF_1"],  # mf_text_inputs
            [""],  # spec_text_inputs
            ["disabled"],  # checkbox_value
        )

        data, columns, tooltip_data, style, selected_rows, checkbox_value, _ = result
        assert len(data) == 1
        assert data[0]["MF ID"] == "MF_1"
        assert checkbox_value == []


def test_mg_table_toggle_selection(sample_processed_data):
    data = json.loads(sample_processed_data)
    original_rows = data["mf_data"]
    filtered_rows = original_rows[:1]

    # Test selecting all rows
    result = mg_table_toggle_selection(["disabled"], original_rows, filtered_rows)
    assert result == [0]  # Should select indices of rows matching the filter

    # Test deselecting all rows
    result = mg_table_toggle_selection([], original_rows, filtered_rows)
    assert result == []

    # Test with None filtered_rows
    result = mg_table_toggle_selection(["disabled"], original_rows, None)
    assert result == list(range(len(original_rows)))  # Should select all rows in original_rows

    # Test with empty value (deselecting when no filter is applied)
    result = mg_table_toggle_selection([], original_rows, None)
    assert result == []


def test_mg_table_select_rows(sample_processed_data):
    data = json.loads(sample_processed_data)
    rows = data["mf_data"]
    selected_rows = [0, 1]

    output1, output2 = mg_table_select_rows(rows, selected_rows)
    assert output1 == f"Total rows: {len(rows)}"
    assert output2.startswith(f"Selected rows: {len(selected_rows)}\n")

    # Test with no rows
    output1, output2 = mg_table_select_rows([], None)
    assert output1 == "No data available."
    assert output2 == "No rows selected."


def test_mg_generate_excel_error_handling():
    """Test the mg_generate_excel function error handling."""
    table_data = [{"MF ID": 1, "gcf_ids_str": "123"}]
    detailed_data = {"1": {"spectrum_ids": ["123"]}}

    with (
        patch("app.callbacks.ctx") as mock_ctx,
        patch("app.callbacks.pd.ExcelWriter") as mock_writer,
    ):
        mock_ctx.triggered = True
        # Simulate an error during Excel generation
        mock_writer.side_effect = Exception("Excel write error")

        result = mg_generate_excel(1, table_data, detailed_data)

        # Should return an error message
        assert result[0] is None
        assert result[1] is True  # Alert is open
        assert "Error generating Excel file" in result[2]
