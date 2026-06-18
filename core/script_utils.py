"""Utilities for parsing and validating Opentrons Python scripts."""

import re
import ast
from typing import Tuple, Optional, List, Dict


def extract_csv_from_script(script_content: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract CSV content from an Opentrons Python script.

    Looks for: csv_raw = (triple quotes)...(triple quotes)
    Supports both single and double triple quotes.

    Returns:
        Tuple of (csv_content, error_message)
        If successful, returns (csv_string, None)
        If failed, returns (None, error_message)
    """
    # Pattern to match csv_raw = '''...''' or csv_raw = """..."""
    # Using re.DOTALL to match across multiple lines
    pattern = r"csv_raw\s*=\s*(?:'''(.*?)'''|\"\"\"(.*?)\"\"\")"

    match = re.search(pattern, script_content, re.DOTALL)

    if not match:
        return None, "Could not find 'csv_raw = '''...''' or 'csv_raw = \"\"\"...\"\"\"' in the script"

    # Extract whichever group matched (single or double quotes)
    csv_content = match.group(1) if match.group(1) is not None else match.group(2)

    if not csv_content or not csv_content.strip():
        return None, "Found csv_raw but it appears to be empty"

    # Check if it contains the placeholder (meaning it hasn't been filled yet)
    if '[CUSTOM CONFIG]' in csv_content:
        return None, "Script contains placeholder '[CUSTOM CONFIG]' - please use a script with actual CSV data"

    return csv_content.strip(), None


def extract_labware_config(script_content: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Extract labware configuration from OT-2 script.

    Returns:
        Tuple of (labware_dict, error_message)
        labware_dict maps slot numbers to labware types
        If failed, returns (None, error_message)
    """
    try:
        tree = ast.parse(script_content)
    except SyntaxError as e:
        return None, f"Script has syntax errors: {str(e)}"

    labware_config = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if this is a protocol.load_labware() call
            if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'load_labware'):

                # Extract labware type (first argument)
                labware_type = None
                if node.args and isinstance(node.args[0], ast.Constant):
                    labware_type = node.args[0].value

                # Extract location (keyword argument or second positional argument)
                location = None
                # Check keyword arguments first
                for keyword in node.keywords:
                    if keyword.arg == 'location':
                        if isinstance(keyword.value, ast.Constant):
                            location = str(keyword.value.value)

                # If not found in keywords, check second positional argument
                if location is None and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    location = str(node.args[1].value)

                if labware_type and location:
                    labware_config[location] = labware_type

    if not labware_config:
        return None, "Could not find any load_labware() calls in the script"

    return labware_config, None


def validate_ot2_labware(script_content: str) -> Tuple[bool, List[str]]:
    """
    Validate OT-2 script has expected labware configuration.

    Expected:
    - 3 tube racks (24+ positions) in slots 4, 5, 6
    - 1 well plate (24+ wells) in slot 2

    Returns:
        Tuple of (is_valid, list_of_warnings)
        is_valid=True if critical requirements met
        warnings contains any configuration differences
    """
    warnings = []

    labware_config, error = extract_labware_config(script_content)
    if error:
        return False, [error]

    labware_loads = [{'type': v, 'location': k} for k, v in labware_config.items()]

    # Check for required tube racks in slots 4, 5, 6
    expected_rack_slots = ['4', '5', '6']
    found_racks = [lw for lw in labware_loads if lw['location'] in expected_rack_slots]

    if len(found_racks) < 3:
        warnings.append(f"Expected 3 tube racks in slots 4, 5, 6 but found only {len(found_racks)}")

    # Check rack types
    expected_rack_type = "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap"
    for rack in found_racks:
        if '24' not in rack['type'] and 'tuberack' in rack['type'].lower():
            warnings.append(f"Slot {rack['location']}: Expected 24-position tube rack")
        elif rack['type'] != expected_rack_type:
            warnings.append(f"Slot {rack['location']}: Using '{rack['type']}' instead of expected '{expected_rack_type}'")

    # Check for output plate in slot 2
    slot_2_labware = [lw for lw in labware_loads if lw['location'] == '2']

    if not slot_2_labware:
        warnings.append("Expected output plate in slot 2 but none found")
    else:
        plate = slot_2_labware[0]
        expected_plate_type = "corning_24_wellplate_3.4ml_flat"

        if '24' not in plate['type'] and 'wellplate' in plate['type'].lower():
            warnings.append("Slot 2: Expected 24-well plate")
        elif plate['type'] != expected_plate_type:
            warnings.append(f"Slot 2: Using '{plate['type']}' instead of expected '{expected_plate_type}'")

    # Valid if we found the critical components (even with warnings)
    is_valid = len(found_racks) >= 3 and len(slot_2_labware) >= 1

    return is_valid, warnings


def prepare_script_for_export(template_script: str, new_csv_content: str) -> str:
    """
    Replace CSV content in template script with new CSV content.

    Replaces the content between csv_raw = triple-quotes
    Standardizes to single quotes in output.

    Args:
        template_script: Original script with csv_raw
        new_csv_content: New CSV content to insert

    Returns:
        Updated script with new CSV content
    """
    # Pattern to find and replace csv_raw = '''...''' or csv_raw = """..."""
    pattern = r"(csv_raw\s*=\s*)(?:'''.*?'''|\"\"\".*?\"\"\")"

    # Replacement with single quotes, standardized
    replacement = f"\\1'''{new_csv_content}'''"

    updated_script = re.sub(pattern, replacement, template_script, flags=re.DOTALL)

    return updated_script
