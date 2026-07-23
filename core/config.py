"""Configuration and constants for the application."""

from typing import List, Dict, Any, Optional

# Column names
CIRCUIT_NAME = 'Circuit name'
TRANSFECTION_GROUP = 'Transfection group'
TRANSFECTION_TYPE = 'Transfection type'
DNA_PART_NAME = 'Contents'
CONCENTRATION = 'Concentration (ng/uL)'
QUANTITY_DNA = 'DNA wanted (ng)'
DNA_ORIGIN = 'DNA source'
DNA_DESTINATION = 'DNA destination'
TRANSFECTION_DESTINATION = 'L3K/OM MM destination'
PLATE_DESTINATION = 'Plate destination'
DILUTED_SOURCE = 'Diluted source'

ALL_COLUMNS = [
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION,
    DILUTED_SOURCE
]

OT2_SCRIPT_COLUMN_ORDER = [
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION,
    TRANSFECTION_TYPE,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA,
    DILUTED_SOURCE
]

# Minimal required columns (locations auto-assigned)
REQUIRED_COLUMNS = {
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA
}

# Legacy specification format: explicit slot assignments but not circuit/group names
REQUIRED_COLUMNS_FULL = {
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA
}

MAX_CIRCUIT_DNA = 800

# Biocompiler Predict API - known DNA part types
# ERN (endonuclease) parts
ERN_PARTS = {'CasE', 'Csy4', 'PgU'}
# Marker (fluorescent protein) parts - used as inputs
MARKER_PARTS = {'mNeonGreen', 'mNG', 'eBFP2', 'PacBlue', 'mCherry', 'mKO2', 'mMaroon1'}

# Dilution threshold configuration
# Dilution is required when DNA_wanted (ng) < MIN_PIPETTE_VOLUME_UL * Concentration (ng/µL)
MIN_PIPETTE_VOLUME_UL = 1

PLATE_COLORS = {
    'dna_part': '99e0a7',
    'diluted_source': 'd0f7d8',
    'destination': 'ADD8E6',
    'circuit': 'FFB6C1',
    'empty': 'D3D3D3',
    'reagent': 'DAB1DA'
}

# Layout definitions
LAYOUT_24TUBE: Dict[str, Any] = {
    'name': '24-Tube Racks (v3.8/v3.9)',
    'input_racks': [
        {'slot': 4, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'required': True},
        {'slot': 5, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'required': True},
        {'slot': 6, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'required': True},
    ],
    'output_plates': [
        {'slot': 2, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'corning_24_wellplate_3.4ml_flat', 'required': True},
        {'slot': 3, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'corning_24_wellplate_3.4ml_flat', 'required': False},
    ],
    'reagent_slots': ["D1.3", "D2.3", "D3.3", "D4.3", "D5.3", "D6.3"],
    'reagent_labels': {
        "D1.3": "Empty tube",
        "D2.3": "Empty tube",
        "D3.3": "L3000",
        "D4.3": "P3000",
        "D5.3": "Opti-MEM",
        "D6.3": "Opti-MEM"
    }
}

LAYOUT_96WELL: Dict[str, Any] = {
    'name': '96-Well Plates (High-Throughput)',
    'input_racks': [
        {'slot': 4, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'required': True},
        {'slot': 5, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'required': True},
        {'slot': 6, 'rows': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], 'cols': list(range(1, 13)), 'labware_type': 'thermoscientific_96_wellplate_800ul', 'required': True},
    ],
    'output_plates': [
        {'slot': 2, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'corning_24_wellplate_3.4ml_flat', 'required': True},
        {'slot': 3, 'rows': ['A', 'B', 'C', 'D'], 'cols': list(range(1, 7)), 'labware_type': 'corning_24_wellplate_3.4ml_flat', 'required': False},
    ],
    'reagent_slots': ["C6.2", "D1.2", "D2.2", "D3.2", "D4.2", "D5.2", "D6.2"],
    'reagent_labels': {
        "C6.2": "H2O",
        "D1.2": "Empty tube",
        "D2.2": "Empty tube",
        "D3.2": "L3000",
        "D4.2": "P3000",
        "D5.2": "Opti-MEM",
        "D6.2": "Opti-MEM"
    }
}

# Layout registry
LAYOUT_REGISTRY: Dict[str, Dict[str, Any]] = {
    '24tube': LAYOUT_24TUBE,
    '96well': LAYOUT_96WELL
}


def _matches_layout(labware_config: Dict[str, str], layout: Dict[str, Any]) -> bool:
    """
    Check if labware_config is compatible with a layout definition.

    Uses flexible matching with required slots:
    - Slots marked as required=True must be present
    - Slots marked as required=False are optional
    - Present slots must match the expected labware type

    Args:
        labware_config: Dictionary mapping slot numbers to labware types
        layout: Layout configuration dictionary

    Returns:
        True if compatible, False otherwise
    """
    # Check all input racks
    for rack in layout['input_racks']:
        slot = str(rack['slot'])
        expected_type = rack['labware_type']
        is_required = rack.get('required', True)  # Default to required if not specified

        if slot in labware_config:
            # Slot is present - must match expected type
            if labware_config[slot] != expected_type:
                return False
        else:
            # Slot is missing - only OK if not required
            if is_required:
                return False

    # Check all output plates
    for plate in layout['output_plates']:
        slot = str(plate['slot'])
        expected_type = plate['labware_type']
        is_required = plate.get('required', True)  # Default to required if not specified

        if slot in labware_config:
            # Slot is present - must match expected type
            if labware_config[slot] != expected_type:
                return False
        else:
            # Slot is missing - only OK if not required
            if is_required:
                return False

    return True


def _format_found_labware(labware_config: Dict[str, str]) -> str:
    """Format found labware for error message."""
    lines = ["Found labware:"]
    for slot in sorted(labware_config.keys(), key=int):
        lines.append(f"  Slot {slot}: {labware_config[slot]}")
    return "\n".join(lines)


def _format_supported_layouts() -> str:
    """Format supported layouts for error message."""
    lines = ["Supported layouts:"]
    for layout_key, layout in LAYOUT_REGISTRY.items():
        lines.append(f"\n{layout['name']} ({layout_key}):")
        lines.append("  Input racks:")
        for rack in layout['input_racks']:
            lines.append(f"    Slot {rack['slot']}: {rack['labware_type']}")
        lines.append("  Output plates:")
        for plate in layout['output_plates']:
            lines.append(f"    Slot {plate['slot']}: {plate['labware_type']}")
    return "\n".join(lines)


def _check_slot_mismatch(slot: str, expected: str, actual: Optional[str]) -> Optional[str]:
    """Check for a single slot mismatch and return formatted error if found."""
    if actual != expected:
        if actual is None:
            return f"  Slot {slot}: missing (expected {expected})"
        return f"  Slot {slot}: found {actual} (expected {expected})"
    return None


def _format_mismatches(labware_config: Dict[str, str]) -> str:
    """Format mismatches for error message."""
    lines = ["Mismatches:"]
    for layout_key, layout in LAYOUT_REGISTRY.items():
        mismatches = []

        # Check all slots (input racks and output plates)
        for item in layout['input_racks'] + layout['output_plates']:
            slot = str(item['slot'])
            mismatch = _check_slot_mismatch(slot, item['labware_type'], labware_config.get(slot))
            if mismatch:
                mismatches.append(mismatch)

        if mismatches:
            lines.append(f"  {layout['name']}:")
            lines.extend(mismatches)

    return "\n".join(lines)


def _generate_mismatch_error(labware_config: Dict[str, str]) -> str:
    """Generate helpful error message showing what didn't match."""
    return "\n\n".join([
        "Labware configuration does not match any supported layout.",
        _format_found_labware(labware_config),
        _format_supported_layouts(),
        _format_mismatches(labware_config)
    ])


def detect_layout_from_labware(labware_config: Dict[str, str]) -> str:
    """
    Detect layout type by exact matching against all supported layouts.

    Args:
        labware_config: Dictionary mapping slot numbers to labware types

    Returns:
        Layout key ('24tube' or '96well')

    Raises:
        ValueError: If labware doesn't exactly match any supported layout
    """
    # Try to match against each supported layout
    for layout_key, layout in LAYOUT_REGISTRY.items():
        if _matches_layout(labware_config, layout):
            return layout_key

    # No match found - provide helpful error
    raise ValueError(_generate_mismatch_error(labware_config))


def get_layout(layout_key: str = '24tube') -> Dict[str, Any]:
    """
    Get layout configuration by key.

    Args:
        layout_key: Layout identifier ('24tube' or '96well')

    Returns:
        Layout configuration dictionary
    """
    return LAYOUT_REGISTRY.get(layout_key, LAYOUT_24TUBE)
