"""
Regression tests for verifying all example files behave as expected.
Run with: pytest tests/regression/test_example_files.py -v
"""
import pytest
import pandas as pd
from pathlib import Path
from io import StringIO

from core.validation import validate_experiment_design
from core.json_converter import parse_json
from core.script_utils import extract_csv_from_script, extract_labware_config
from core.config import detect_layout_from_labware


# Test cases: (filepath, should_pass, layout_key)
# layout_key is optional - defaults to '24tube' if not specified
EXAMPLE_TEST_CASES = [
    # Minimal format
    ("minimal/valid/simple_two_circuits.csv", True, '24tube'),
    ("minimal/valid/large_five_circuits.csv", True, '24tube'),
    ("minimal/valid/with_plate_destinations.csv", True, '24tube'),
    ("minimal/valid/with_dilution.csv", True, '24tube'),
    ("minimal/invalid/empty_required_fields.csv", False, '24tube'),
    ("minimal/invalid/circuit_dna_over_limit.csv", False, '24tube'),

    # Full format
    ("full/valid/small_explicit_slots.csv", True, '24tube'),
    ("full/valid/large_explicit_slots.csv", True, '24tube'),
    ("full/valid/96well_explicit_slots.csv", True, '96well'),
    ("full/valid/with_manual_dilutions.csv", True, '24tube'),
    ("full/valid/legacy_format_inferred.csv", True, '24tube'),
    ("full/invalid/duplicate_input_slots.csv", False, '24tube'),
    # Note: inconsistent_mappings.csv is actually VALID (same source can go to multiple destinations)
    ("full/invalid/inconsistent_mappings.csv", True, '24tube'),
    ("full/invalid/cross_column_conflict.csv", False, '24tube'),
    ("full/invalid/grouping_violation_dna_part.csv", False, '24tube'),
    ("full/invalid/grouping_violation_circuit.csv", False, '24tube'),
    ("full/invalid/96well_wrong_pool_dna_source.csv", False, '96well'),
    ("full/invalid/96well_wrong_pool_dna_dest.csv", False, '96well'),
    ("full/invalid/invalid_slot_for_layout.csv", False, '24tube'),

    # Opentrons scripts - valid
    ("opentrons/valid/simple_24tube.py", True, None),
    ("opentrons/valid/complex_24tube.py", True, None),
    ("opentrons/valid/96well_layout.py", True, None),
    ("opentrons/valid/minimal_format_24tube.py", True, None),  # Minimal CSV format (Circuit name, Transfection group)
    ("opentrons/valid/24tube_no_slot3.py", True, None),
    ("opentrons/valid/minimal_hardware_96well.py", True, None),  # Minimal hardware (only required slots loaded)
    ("opentrons/valid/minimal_format_96well.py", True, None),  # Minimal CSV format (Circuit name, Transfection group)
    ("opentrons/valid/96well_no_slot3.py", True, None),
    # 96well_no_slot6.py was moved to invalid/ folder

    # Opentrons scripts - invalid
    ("opentrons/invalid/minimal_hardware_24tube.py", False, None),  # Missing required rack 2 (slot 5)
    ("opentrons/invalid/24tube_no_slot6.py", False, None),  # Missing required slot 6
    ("opentrons/invalid/24tube_no_slot3_no_slot6.py", False, None),  # Missing required slot 6
    ("opentrons/invalid/missing_csv_raw.py", False, None),
    ("opentrons/invalid/no_input_racks.py", False, None),
    ("opentrons/invalid/no_output_plate.py", False, None),
    ("opentrons/invalid/24tube_missing_slot2.py", False, None),
    ("opentrons/invalid/24tube_missing_slot4.py", False, None),
    ("opentrons/invalid/96well_missing_slot5.py", False, None),
    ("opentrons/invalid/wrong_slot4_type.py", False, None),
    # mixed_input_types.py now matches 96well layout (slots 4,5 = tube racks, slot 6 = 96-well)
    ("opentrons/invalid/mixed_input_types.py", True, None),

    # Biocompiler JSON
    # Note: Valid JSON files correctly fail validation because concentration is None
    # This is expected - users must manually add concentrations after JSON import
    ("biocompiler/valid/single_circuit.json5", False, '24tube'),  # Fails: no concentration
    ("biocompiler/valid/multiple_circuits.json5", False, '24tube'),  # Fails: no concentration
    ("biocompiler/invalid/missing_required_fields.json5", False, '24tube'),
    ("biocompiler/invalid/invalid_structure.json5", False, '24tube'),
    ("biocompiler/invalid/missing_ratio.json5", False, '24tube'),
]


@pytest.fixture
def example_base_path():
    """Base path for example input files."""
    return Path("tests/example_input")


def validate_csv_file(filepath, layout_key='24tube'):
    """Validate a CSV file and return (is_valid, errors)."""
    df = pd.read_csv(filepath)
    is_valid, error_msg = validate_experiment_design(df, layout_key)
    errors = [error_msg] if error_msg else []
    return not bool(errors), errors


def validate_json_file(filepath, layout_key='24tube'):
    """Validate a JSON5 file and return (is_valid, errors)."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        df = parse_json(content)
        is_valid, error_msg = validate_experiment_design(df, layout_key)
        errors = [error_msg] if error_msg else []
        return not bool(errors), errors
    except Exception as e:
        # Exception means invalid JSON structure (expected for some test cases)
        return False, [str(e)]


def validate_opentrons_script(filepath):
    """Validate an Opentrons Python script and return (is_valid, errors)."""
    with open(filepath, 'r') as f:
        script_content = f.read()

    # Extract and validate labware configuration
    labware_config, labware_error = extract_labware_config(script_content)
    if labware_error:
        return False, [labware_error]

    if not labware_config:
        return False, ["No labware configuration found in script"]

    # Detect layout from labware
    try:
        layout_key = detect_layout_from_labware(labware_config)
    except ValueError as e:
        return False, [str(e)]

    # Extract CSV
    csv_content, extraction_error = extract_csv_from_script(script_content)
    if extraction_error or not csv_content:
        return False, [extraction_error or "No CSV data found in script"]

    # Parse CSV content
    df = pd.read_csv(StringIO(csv_content))
    is_valid, error_msg = validate_experiment_design(df, layout_key, labware_config)
    errors = [error_msg] if error_msg else []
    return not bool(errors), errors


@pytest.mark.parametrize("filepath_str,should_pass,layout_key", EXAMPLE_TEST_CASES,
                         ids=[f"{p[0]}:{'PASS' if p[1] else 'FAIL'}" for p in EXAMPLE_TEST_CASES])
def test_example_file(example_base_path, filepath_str, should_pass, layout_key):
    """Test that example files validate as expected."""
    filepath = example_base_path / filepath_str

    # Determine file type and validate
    if filepath.suffix == '.csv':
        is_valid, errors = validate_csv_file(filepath, layout_key or '24tube')
    elif filepath.suffix == '.json5':
        is_valid, errors = validate_json_file(filepath, layout_key or '24tube')
    elif filepath.suffix == '.py':
        is_valid, errors = validate_opentrons_script(filepath)
    else:
        pytest.fail(f"Unknown file type: {filepath.suffix}")

    # Check result matches expectation
    if should_pass:
        assert is_valid, f"Expected file to pass validation but got errors: {errors[0] if errors else 'Unknown'}"
    else:
        assert not is_valid, f"Expected file to fail validation but it passed"
