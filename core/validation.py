"""Validation logic for experiment designs."""

import pandas as pd
from typing import Tuple, Optional, List, Dict, Set
from collections import defaultdict

from .config import (
    REQUIRED_COLUMNS,
    REQUIRED_COLUMNS_FULL,
    MAX_CIRCUIT_DNA,
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    DNA_PART_NAME,
    QUANTITY_DNA,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION,
    DILUTED_SOURCE,
    get_layout,
)
from .utils import (
    normalize_column_name,
    normalize_well_format,
    normalize_for_comparison,
    normalized_groupby,
)


class SlotValidator:
    """Validates slot assignments against layout constraints."""

    def __init__(self, layout_key: str, labware_config: Dict[str, str]):
        """
        Initialize validator with layout configuration.

        Args:
            layout_key: Layout type ('24tube' or '96well')
            labware_config: Dictionary mapping slot numbers to labware types
        """
        from .layout import get_layout_aware_slot_pools

        self.layout_key = layout_key
        self.layout = get_layout(layout_key)
        self.labware_config = labware_config or {}

        # Get reagent slots from static layout configuration
        self.reagent_slots = set(self.layout.get('reagent_slots', []))

        # Build slot pools
        slot_pools = get_layout_aware_slot_pools(layout_key, self.layout, list(self.reagent_slots))

        if layout_key == '96well':
            # For 96well: separate tubes (slot 4) from wells (slots 5, 6)
            self.valid_dna_source_slots = set(slot_pools['input_dna_slots'])  # Tube rack only
            self.valid_working_slots = set(slot_pools['working_slots'])  # Well plates only
        else:
            # For 24tube: all input racks are tubes (shared pool)
            all_input = set(slot_pools['input_dna_slots'])
            self.valid_dna_source_slots = all_input
            self.valid_working_slots = all_input

        # Output slots (separate from input)
        from .layout import get_output_slots
        self.valid_output_slots = set(get_output_slots(self.layout['output_plates']))

    def get_valid_slots_for_column(self, column: str) -> Set[str]:
        """Get set of valid slots for a given column."""
        if column == DNA_ORIGIN:
            return self.valid_dna_source_slots
        elif column in [DNA_DESTINATION, TRANSFECTION_DESTINATION, DILUTED_SOURCE]:
            return self.valid_working_slots
        elif column == PLATE_DESTINATION:
            return self.valid_output_slots
        else:
            return set()

    def validate_slot_exists_in_layout(self, slot: str, column: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a slot is valid for its column in this layout.

        Returns:
            (is_valid, error_message)
        """
        valid_slots = self.get_valid_slots_for_column(column)

        if slot in valid_slots:
            return True, None

        # Generate helpful error message
        if column == DNA_ORIGIN and self.layout_key == '96well':
            return False, "must be in tube rack (rack 1), not in well plates"
        elif column in [DNA_DESTINATION, TRANSFECTION_DESTINATION, DILUTED_SOURCE] and self.layout_key == '96well':
            return False, "must be in well plates (racks 2-3), not in tube rack"
        elif slot in self.reagent_slots:
            return False, "conflicts with reserved reagent slot"
        else:
            return False, "is not a valid slot for this layout"


def _collect_existing_slots(df: pd.DataFrame, column: str) -> Dict[int, str]:
    """
    Collect existing (non-empty) slots from a column.

    Returns:
        Dict mapping row index to normalized slot
    """
    if column not in df.columns:
        return {}

    slots = {}
    for idx, value in df[column].items():
        if pd.notna(value) and str(value).strip():
            slots[idx] = normalize_well_format(str(value).strip())
    return slots


def _validate_layout_compatibility(
    df: pd.DataFrame,
    validator: SlotValidator
) -> List[str]:
    """
    Validate that all existing slots are compatible with the selected layout.

    Checks:
    - DNA sources must be in appropriate input slots (tubes for 96well)
    - DNA/L3K/Dilution destinations must be in appropriate working slots (wells for 96well)
    - Plate destinations must be in output plate slots
    - No slots conflict with reserved reagent positions
    """
    errors = []

    slot_columns = [DNA_ORIGIN, DNA_DESTINATION, TRANSFECTION_DESTINATION,
                    PLATE_DESTINATION, DILUTED_SOURCE]

    for column in slot_columns:
        existing_slots = _collect_existing_slots(df, column)

        for row_idx, slot in existing_slots.items():
            is_valid, error_msg = validator.validate_slot_exists_in_layout(slot, column)
            if not is_valid:
                errors.append(
                    f"• Slot '{slot}' in {column} (row {row_idx + 1}) {error_msg}"
                )

    return errors


def _validate_global_uniqueness(df: pd.DataFrame) -> List[str]:
    """
    Validate that no slot is used in multiple different ways.

    Rules:
    - Within each column: same slot can only map to one entity (DNA part, Circuit/Group, etc.)
    - Across columns IN THE SAME POOL: same slot cannot be used in different columns
    - Input pool (DNA source, DNA dest, L3K dest, Dilution source) is separate from output pool (Plate dest)

    BUT: Same slot appearing multiple times in same column for same entity is OK!
    """
    errors = []

    # Column -> entity mappings, grouped by pool
    input_columns = {
        DNA_ORIGIN: DNA_PART_NAME,
        DNA_DESTINATION: (CIRCUIT_NAME, TRANSFECTION_GROUP),
        TRANSFECTION_DESTINATION: (CIRCUIT_NAME, TRANSFECTION_GROUP),
        DILUTED_SOURCE: DNA_PART_NAME,
    }

    output_columns = {
        PLATE_DESTINATION: CIRCUIT_NAME,
    }

    # Helper to validate a pool of columns
    def validate_pool(column_entity_map: Dict, pool_name: str) -> List[str]:
        pool_errors = []
        slot_usage = defaultdict(list)

        # Collect all slot usages in this pool
        for column, entity_cols in column_entity_map.items():
            existing_slots = _collect_existing_slots(df, column)

            # Skip if entity columns don't exist in dataframe
            if isinstance(entity_cols, tuple):
                if not all(col in df.columns for col in entity_cols):
                    continue
            else:
                if entity_cols not in df.columns:
                    continue

            for row_idx, slot in existing_slots.items():
                # Get entity for this row
                if isinstance(entity_cols, tuple):
                    entity = tuple(normalize_for_comparison(df.at[row_idx, col])
                                   for col in entity_cols)
                    entity_display = '/'.join(str(df.at[row_idx, col]) for col in entity_cols)
                else:
                    entity = normalize_for_comparison(df.at[row_idx, entity_cols])
                    entity_display = str(df.at[row_idx, entity_cols])

                slot_usage[slot].append((column, row_idx + 1, entity, entity_display))

        # Check for conflicts within this pool
        for slot, usages in slot_usage.items():
            # Group by column
            by_column = defaultdict(list)
            for column, row, entity, entity_display in usages:
                by_column[column].append((row, entity, entity_display))

            # Cross-column conflict check (within pool only)
            if len(by_column) > 1:
                conflict_desc = []
                for column, items in by_column.items():
                    rows = [str(r) for r, _, _ in items]
                    entity_display = items[0][2]  # Use first entity's display name
                    conflict_desc.append(f"{column} (rows {', '.join(rows)}, {entity_display})")

                pool_errors.append(
                    f"• Slot '{slot}' used in multiple {pool_name} columns:\n  " +
                    '\n  '.join(conflict_desc)
                )

            # Within-column conflict check (same slot, different entities)
            for column, items in by_column.items():
                unique_entities = set(entity for _, entity, _ in items)
                if len(unique_entities) > 1:
                    entity_displays = [entity_display for _, _, entity_display in items]
                    rows = [str(r) for r, _, _ in items]
                    pool_errors.append(
                        f"• Slot '{slot}' in {column} assigned to multiple entities: " +
                        f"{list(set(entity_displays))} (rows {', '.join(rows)})"
                    )

        return pool_errors

    # Validate input pool and output pool separately
    errors.extend(validate_pool(input_columns, "input"))
    errors.extend(validate_pool(output_columns, "output"))

    return errors


def _validate_grouping_consistency(df: pd.DataFrame) -> List[str]:
    """
    Validate that each entity (DNA part, Circuit/Group combo, Circuit) maps to exactly one slot.

    Rules:
    - If DNA part "GFP" has slot A1.1 in any row, all other rows with "GFP" must have A1.1 or blank
    - If Circuit1/X1 has slot A2.2 in any row, all rows with Circuit1/X1 must have A2.2 or blank
    - Similar for all other groupings

    Blanks are OK - they will be filled during assignment.
    """
    errors = []

    groupings = [
        (DNA_ORIGIN, [DNA_PART_NAME], "DNA part"),
        (DNA_DESTINATION, [CIRCUIT_NAME, TRANSFECTION_GROUP], "Circuit/Group"),
        (TRANSFECTION_DESTINATION, [CIRCUIT_NAME, TRANSFECTION_GROUP], "Circuit/Group"),
        (PLATE_DESTINATION, [CIRCUIT_NAME], "Circuit"),
        (DILUTED_SOURCE, [DNA_PART_NAME], "DNA part"),
    ]

    for slot_column, group_columns, entity_name in groupings:
        if slot_column not in df.columns:
            continue

        # Skip if all required group columns don't exist
        if not all(col in df.columns for col in group_columns):
            continue

        # Build entity -> slots mapping (normalized for case-insensitive comparison)
        entity_slots = defaultdict(set)
        entity_display_names = {}  # Track original names for error messages

        for idx, row in df.iterrows():
            # Get normalized entity key
            if len(group_columns) == 1:
                entity_key = normalize_for_comparison(row[group_columns[0]])
                entity_display = str(row[group_columns[0]])
            else:
                entity_key = tuple(normalize_for_comparison(row[col]) for col in group_columns)
                entity_display = '/'.join(str(row[col]) for col in group_columns)

            # Track display name
            if entity_key not in entity_display_names:
                entity_display_names[entity_key] = entity_display

            # Get slot (skip if blank)
            slot_value = row.get(slot_column, '')
            if pd.notna(slot_value) and str(slot_value).strip():
                normalized_slot = normalize_well_format(str(slot_value).strip())
                entity_slots[entity_key].add(normalized_slot)

        # Check for conflicts (entity with multiple different slots)
        for entity_key, slots in entity_slots.items():
            if len(slots) > 1:
                entity_display = entity_display_names[entity_key]
                errors.append(
                    f"• {entity_name} '{entity_display}' has multiple {slot_column} slots: " +
                    f"{sorted(slots)} (must have exactly one)"
                )

    return errors


def _validate_circuit_dna_limits(df: pd.DataFrame) -> List[str]:
    """Validate that total DNA per circuit doesn't exceed MAX_CIRCUIT_DNA."""
    errors = []

    if CIRCUIT_NAME not in df.columns or QUANTITY_DNA not in df.columns:
        return errors

    df_with_circuit = df[df[CIRCUIT_NAME].notna()].copy()
    if len(df_with_circuit) == 0:
        return errors

    with normalized_groupby(df_with_circuit, CIRCUIT_NAME) as grouped:
        circuit_sums = grouped[QUANTITY_DNA].sum()

    for circuit_key, total in circuit_sums.items():
        if total > MAX_CIRCUIT_DNA:
            # Get original circuit name for display
            original_circuit = df_with_circuit[
                df_with_circuit[CIRCUIT_NAME].apply(normalize_for_comparison) == circuit_key
            ][CIRCUIT_NAME].iloc[0]
            errors.append(
                f"• Circuit '{original_circuit}' exceeds {MAX_CIRCUIT_DNA}ng limit: {total:.1f}ng"
            )

    return errors


def validate_experiment_design(
    df: pd.DataFrame,
    layout_key: str = '24tube',
    labware_config: Dict[str, str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate experiment design before generating layouts.

    This validates ONLY existing values in the table, not missing values.
    Missing values will be filled during layout generation.

    Args:
        df: Experiment design dataframe
        layout_key: Layout type ('24tube' or '96well')
        labware_config: Dictionary mapping slot numbers to labware types

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if valid, otherwise contains categorized errors
    """
    all_errors = []

    # Check required columns exist
    normalized_cols = {normalize_column_name(col) for col in df.columns}
    minimal_normalized = {normalize_column_name(col) for col in REQUIRED_COLUMNS}
    full_normalized = {normalize_column_name(col) for col in REQUIRED_COLUMNS_FULL}

    has_minimal = minimal_normalized.issubset(normalized_cols)
    has_full = full_normalized.issubset(normalized_cols)

    if not has_minimal and not has_full:
        missing_minimal = minimal_normalized - normalized_cols
        missing_full = full_normalized - normalized_cols
        return False, (
            f"Missing required columns. Need either:\n"
            f"  - Minimal format: {', '.join(sorted(missing_minimal))}\n"
            f"  - OR Full format: {', '.join(sorted(missing_full))}"
        )

    # Check required fields not empty
    required_field_errors = []
    if has_minimal:
        for field in REQUIRED_COLUMNS:
            if field in df.columns:
                empty_rows = df[df[field].isna() | (df[field] == '')]
                if len(empty_rows) > 0:
                    row_nums = ', '.join(str(r + 1) for r in empty_rows.index.tolist())
                    required_field_errors.append(f"• {field} cannot be empty (rows: {row_nums})")

    if required_field_errors:
        all_errors.append("[Required Field Errors]\n" + '\n'.join(required_field_errors))

    # Create validator
    validator = SlotValidator(layout_key, labware_config)

    # Category 1: Layout Compatibility
    layout_errors = _validate_layout_compatibility(df, validator)
    if layout_errors:
        all_errors.append("[Layout Compatibility Errors]\n" + '\n'.join(layout_errors))

    # Category 2: Global Uniqueness (within and across columns)
    uniqueness_errors = _validate_global_uniqueness(df)
    if uniqueness_errors:
        all_errors.append("[Slot Conflict Errors]\n" + '\n'.join(uniqueness_errors))

    # Category 3: Grouping Consistency
    grouping_errors = _validate_grouping_consistency(df)
    if grouping_errors:
        all_errors.append("[Grouping Rule Violations]\n" + '\n'.join(grouping_errors))

    # Category 4: Circuit DNA Limits
    circuit_errors = _validate_circuit_dna_limits(df)
    if circuit_errors:
        all_errors.append("[Circuit DNA Limit Exceeded]\n" + '\n'.join(circuit_errors))

    if all_errors:
        return False, '\n\n'.join(all_errors)

    return True, None
