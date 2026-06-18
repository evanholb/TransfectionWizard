"""Layout generation logic for slot assignment."""

import pandas as pd
from typing import List, Dict, Any, Tuple

from .config import (
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    TRANSFECTION_TYPE,
    DNA_PART_NAME,
    PLATE_DESTINATION,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    DILUTED_SOURCE,
    CONCENTRATION,
    QUANTITY_DNA,
    MIN_PIPETTE_VOLUME_UL,
    get_layout,
)
from .utils import (
    normalize_well_format,
    normalize_for_comparison,
    normalized_groupby,
)


def get_input_slots(racks_config: List[Dict[str, Any]], reagent_slots: List[str]) -> List[str]:
    """Get all input slot positions, excluding reagent slots."""
    slots = []
    for rack_idx, rack in enumerate(racks_config, start=1):
        for row in rack['rows']:
            for col in rack['cols']:
                slot = f"{row}{col}.{rack_idx}"
                if slot not in reagent_slots:
                    slots.append(slot)
    return slots


def get_output_slots(output_plates: List[Dict[str, Any]]) -> List[str]:
    """Get output plate slot positions from all output plates."""
    slots = []
    for plate_idx, plate in enumerate(output_plates, start=1):
        for row in plate['rows']:
            for col in plate['cols']:
                # Use sequential numbering (1, 2, ...) not slot numbers
                slots.append(f"{row}{col}.{plate_idx}")
    return slots


def get_layout_aware_slot_pools(
    layout_key: str,
    layout: Dict[str, Any],
    reagent_slots: List[str]
) -> Dict[str, List[str]]:
    """
    Get slot pools based on layout type and purpose.

    Returns dict with:
        'input_dna_slots': Where original DNA samples are placed
        'working_slots': Where robot prepares dilutions/mixes

    For 24tube layouts:
        - Both pools reference the same tube racks (slots 4, 5, 6)

    For 96well layouts:
        - input_dna_slots: Tube racks (slots 4 & 5)
        - working_slots: Well plate only (slot 6)

    Args:
        layout_key: '24tube' or '96well'
        layout: Layout configuration dictionary
        reagent_slots: List of reserved reagent slots

    Returns:
        Dictionary with 'input_dna_slots' and 'working_slots' pools
    """
    if layout_key == '24tube':
        # For 24tube, all slots come from same pool (both names reference same list)
        all_slots = get_input_slots(layout['input_racks'], reagent_slots)
        return {
            'input_dna_slots': all_slots,
            'working_slots': all_slots
        }
    elif layout_key == '96well':
        # For 96well, separate tube racks (slots 4 & 5) from well plate (slot 6)
        input_dna_slots = []
        working_slots = []

        for rack_idx, rack in enumerate(layout['input_racks'], start=1):
            rack_slots = []
            for row in rack['rows']:
                for col in rack['cols']:
                    slot = f"{row}{col}.{rack_idx}"
                    if slot not in reagent_slots:
                        rack_slots.append(slot)

            if rack_idx in [1, 2]:  # Racks 1 & 2 (slots 4 & 5) - 24-tube racks for DNA origins
                input_dna_slots.extend(rack_slots)
            else:  # Rack 3 (slot 6) - 96-well plate for working volumes
                working_slots.extend(rack_slots)

        return {
            'input_dna_slots': input_dna_slots,
            'working_slots': working_slots
        }
    else:
        # Default to 24tube behavior
        all_slots = get_input_slots(layout['input_racks'], reagent_slots)
        return {
            'input_dna_slots': all_slots,
            'working_slots': all_slots
        }


def detect_dilutions(df: pd.DataFrame) -> pd.Series:
    """
    Detect which rows require dilution based on minimum pipette volume.

    Dilution is required when the volume needed is too small to pipette accurately.
    Volume = DNA_wanted (ng) / Concentration (ng/µL)

    If volume < MIN_PIPETTE_VOLUME_UL (2µL), then dilution is required.
    This is equivalent to: DNA_wanted < MIN_PIPETTE_VOLUME_UL * Concentration

    Args:
        df: DataFrame with CONCENTRATION and QUANTITY_DNA columns

    Returns:
        Boolean Series indicating which rows need dilution
    """
    if CONCENTRATION not in df.columns or QUANTITY_DNA not in df.columns:
        return pd.Series([False] * len(df), index=df.index)

    # Calculate which rows need dilution
    needs_dilution = pd.Series([False] * len(df), index=df.index)

    for idx, row in df.iterrows():
        try:
            conc = float(row[CONCENTRATION]) if pd.notna(row[CONCENTRATION]) else 0
            dna_wanted = float(row[QUANTITY_DNA]) if pd.notna(row[QUANTITY_DNA]) else 0

            if conc > 0 and dna_wanted > 0:
                # If DNA_wanted < MIN_PIPETTE_VOLUME_UL * Concentration,
                # then volume < MIN_PIPETTE_VOLUME_UL (too small to pipette)
                needs_dilution.at[idx] = dna_wanted < (MIN_PIPETTE_VOLUME_UL * conc)
        except (ValueError, TypeError):
            # If conversion fails, assume no dilution needed
            needs_dilution.at[idx] = False

    return needs_dilution


class SlotAssigner:
    """Manages slot assignment with global conflict tracking."""

    def __init__(self, layout_key: str, config: Dict[str, Any]):
        """
        Initialize slot assigner.

        Args:
            layout_key: Layout type ('24tube' or '96well')
            config: Slot configuration from _prepare_slot_configuration
        """
        self.layout_key = layout_key
        self.config = config

        # Track globally used slots across all assignments
        self.globally_used_input = set(config['reagent_slots'])
        self.globally_used_output = set()  # Output plates are separate

    def _collect_existing_slots_for_group(
        self,
        df: pd.DataFrame,
        slot_column: str,
        grouping_columns: List[str]
    ) -> Dict[Tuple, str]:
        """
        Collect existing slot assignments for each group.

        Returns:
            Dict mapping normalized entity key -> slot
        """
        if slot_column not in df.columns:
            return {}

        entity_to_slot = {}

        for idx, row in df.iterrows():
            # Get normalized entity key
            if len(grouping_columns) == 1:
                entity_key = normalize_for_comparison(row[grouping_columns[0]])
            else:
                entity_key = tuple(normalize_for_comparison(row[col]) for col in grouping_columns)

            # Get slot (skip if blank)
            slot_value = row.get(slot_column, '')
            if pd.notna(slot_value) and str(slot_value).strip():
                normalized_slot = normalize_well_format(str(slot_value).strip())

                # Preserve the first non-blank slot found for this entity
                if entity_key not in entity_to_slot:
                    entity_to_slot[entity_key] = normalized_slot

        return entity_to_slot

    def assign_slots(
        self,
        df: pd.DataFrame,
        slot_column: str,
        grouping_columns: List[str],
        available_slots: List[str],
        is_output_pool: bool = False
    ) -> pd.DataFrame:
        """
        Assign unique slots to groups, preserving existing assignments.

        Args:
            df: DataFrame to update
            slot_column: Column to assign slots to
            grouping_columns: Columns that define groups
            available_slots: Pool of slots to assign from
            is_output_pool: True if assigning from output plates (separate tracking)

        Returns:
            Updated DataFrame with slots assigned
        """
        df = df.copy()

        # Initialize column if needed
        if slot_column not in df.columns:
            df[slot_column] = ''

        # Normalize existing slots
        df[slot_column] = df[slot_column].apply(
            lambda x: normalize_well_format(x) if pd.notna(x) and str(x).strip() else ''
        )

        # Collect existing assignments (entity -> slot mapping)
        entity_to_slot = self._collect_existing_slots_for_group(df, slot_column, grouping_columns)

        # Track which slots are already used (from existing assignments)
        if is_output_pool:
            used_in_pool = set(entity_to_slot.values())
            self.globally_used_output.update(used_in_pool)
            reserved = self.globally_used_output
        else:
            used_in_pool = set(entity_to_slot.values())
            self.globally_used_input.update(used_in_pool)
            reserved = self.globally_used_input

        # Find groups that need slots assigned
        all_entities = []
        for idx, row in df.iterrows():
            if len(grouping_columns) == 1:
                entity_key = normalize_for_comparison(row[grouping_columns[0]])
            else:
                entity_key = tuple(normalize_for_comparison(row[col]) for col in grouping_columns)

            if entity_key not in all_entities:
                all_entities.append(entity_key)

        # Assign slots to entities that don't have them
        available = [s for s in available_slots if s not in reserved]

        for entity_key in all_entities:
            if entity_key not in entity_to_slot:
                # Need to assign a new slot
                if not available:
                    raise ValueError(f"Not enough slots available for {slot_column}")

                new_slot = available.pop(0)
                entity_to_slot[entity_key] = new_slot

                # Mark as used
                if is_output_pool:
                    self.globally_used_output.add(new_slot)
                else:
                    self.globally_used_input.add(new_slot)

        # Apply slot assignments to all rows
        for idx, row in df.iterrows():
            if len(grouping_columns) == 1:
                entity_key = normalize_for_comparison(row[grouping_columns[0]])
            else:
                entity_key = tuple(normalize_for_comparison(row[col]) for col in grouping_columns)

            df.at[idx, slot_column] = entity_to_slot.get(entity_key, '')

        return df

    def assign_dilution_sources(
        self,
        df: pd.DataFrame,
        dilution_mask: pd.Series,
        available_slots: List[str]
    ) -> pd.DataFrame:
        """
        Assign diluted source slots for DNA parts requiring dilution.

        Groups by DNA_PART_NAME and assigns one slot per unique DNA part.
        Clears dilution slots for rows that don't need dilution.

        Args:
            df: Experiment dataframe
            dilution_mask: Boolean Series indicating which rows need dilution
            available_slots: Pool of slots to assign from

        Returns:
            Updated DataFrame
        """
        df = df.copy()

        # Initialize DILUTED_SOURCE column if it doesn't exist
        if DILUTED_SOURCE not in df.columns:
            df[DILUTED_SOURCE] = ''

        # Clear diluted sources for rows that NO LONGER need dilution
        df.loc[~dilution_mask, DILUTED_SOURCE] = ''

        if not dilution_mask.any():
            return df

        # Only process rows that need dilution
        df_needs_dilution = df[dilution_mask].copy()

        # Collect existing dilution slot assignments (by DNA part)
        entity_to_slot = self._collect_existing_slots_for_group(
            df_needs_dilution,
            DILUTED_SOURCE,
            [DNA_PART_NAME]
        )

        # Track which slots are used
        used_in_pool = set(entity_to_slot.values())
        self.globally_used_input.update(used_in_pool)

        # Find DNA parts that need dilution slots
        all_parts = []
        for idx, row in df_needs_dilution.iterrows():
            part_key = normalize_for_comparison(row[DNA_PART_NAME])
            if part_key not in all_parts:
                all_parts.append(part_key)

        # Assign slots to parts that don't have them
        available = [s for s in available_slots if s not in self.globally_used_input]

        for part_key in all_parts:
            if part_key not in entity_to_slot:
                if not available:
                    raise ValueError(f"Not enough slots available for {DILUTED_SOURCE}")

                new_slot = available.pop(0)
                entity_to_slot[part_key] = new_slot
                self.globally_used_input.add(new_slot)

        # Apply assignments to rows needing dilution
        for idx in df_needs_dilution.index:
            part_key = normalize_for_comparison(df.at[idx, DNA_PART_NAME])
            df.at[idx, DILUTED_SOURCE] = entity_to_slot.get(part_key, '')

        return df


def fill_transfection_types(df: pd.DataFrame) -> pd.DataFrame:
    """Fill transfection types: Single (1 DNA part) or Co (multiple)."""
    df = df.copy()

    if TRANSFECTION_TYPE not in df.columns:
        df[TRANSFECTION_TYPE] = ''

    with normalized_groupby(df, [CIRCUIT_NAME, TRANSFECTION_GROUP]) as grouped:
        group_counts = grouped.size()

    for idx, row in df.iterrows():
        if pd.isna(row[TRANSFECTION_TYPE]) or not str(row[TRANSFECTION_TYPE]).strip():
            # Get normalized key for lookup
            key = (normalize_for_comparison(row[CIRCUIT_NAME]),
                   normalize_for_comparison(row[TRANSFECTION_GROUP]))
            count = group_counts.get(key, 1)
            df.at[idx, TRANSFECTION_TYPE] = 'Co' if count > 1 else 'Single'

    return df


def infer_circuits(df: pd.DataFrame) -> pd.DataFrame:
    """Infer circuit names from plate destinations."""
    df = df.copy()

    if CIRCUIT_NAME not in df.columns:
        df[CIRCUIT_NAME] = ''

    missing_circuit = df[CIRCUIT_NAME].isna() | (df[CIRCUIT_NAME] == '')

    if missing_circuit.any():
        # Build mapping from existing data (plate destination → circuit)
        dest_to_circuit = {}
        for _, row in df.iterrows():
            dest = row[PLATE_DESTINATION]
            circuit = row[CIRCUIT_NAME]
            if pd.notna(dest) and str(dest).strip() and pd.notna(circuit) and str(circuit).strip():
                dest_to_circuit[dest] = circuit

        # Find unique destinations that need circuits assigned
        missing_dests = set()
        for _, row in df[missing_circuit].iterrows():
            dest = row[PLATE_DESTINATION]
            if pd.notna(dest) and str(dest).strip() and dest not in dest_to_circuit:
                missing_dests.add(dest)

        # Assign circuits to missing destinations (Circuit1, Circuit2, Circuit3, ...)
        if missing_dests:
            existing_circuits = set(dest_to_circuit.values())
            circuit_num = 1
            for dest in sorted(missing_dests):
                # Find next available circuit number
                while f"Circuit{circuit_num}" in existing_circuits:
                    circuit_num += 1
                dest_to_circuit[dest] = f"Circuit{circuit_num}"
                existing_circuits.add(f"Circuit{circuit_num}")
                circuit_num += 1

        # Apply mapping to rows with missing circuits
        for idx, row in df[missing_circuit].iterrows():
            dest = row[PLATE_DESTINATION]
            if dest in dest_to_circuit:
                df.at[idx, CIRCUIT_NAME] = dest_to_circuit[dest]

    return df


def infer_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Infer transfection groups from DNA destinations."""
    df = df.copy()

    if TRANSFECTION_GROUP not in df.columns:
        df[TRANSFECTION_GROUP] = ''

    missing_group = df[TRANSFECTION_GROUP].isna() | (df[TRANSFECTION_GROUP] == '')

    if missing_group.any():
        # Add temporary normalized circuit key for case-insensitive iteration
        df['_circuit_key'] = df[CIRCUIT_NAME].apply(normalize_for_comparison)

        try:
            for circuit_key in df['_circuit_key'].unique():
                circuit_rows = df[df['_circuit_key'] == circuit_key]
                circuit_missing = (df['_circuit_key'] == circuit_key) & missing_group

                if circuit_missing.any():
                    # Build mapping from existing data (destination → group)
                    dest_to_group = {}
                    for _, row in circuit_rows.iterrows():
                        dest = row[DNA_DESTINATION]
                        group = row[TRANSFECTION_GROUP]
                        if pd.notna(dest) and str(dest).strip() and pd.notna(group) and str(group).strip():
                            dest_to_group[dest] = group

                    # Find unique destinations that need groups assigned
                    missing_dests = set()
                    for _, row in df[circuit_missing].iterrows():
                        dest = row[DNA_DESTINATION]
                        if pd.notna(dest) and str(dest).strip() and dest not in dest_to_group:
                            missing_dests.add(dest)

                    # Assign groups to missing destinations (X1, X2, X3, ...)
                    if missing_dests:
                        existing_groups = set(dest_to_group.values())
                        group_num = 1
                        for dest in sorted(missing_dests):
                            # Find next available group number
                            while f"X{group_num}" in existing_groups:
                                group_num += 1
                            dest_to_group[dest] = f"X{group_num}"
                            existing_groups.add(f"X{group_num}")
                            group_num += 1

                    # Apply mapping to rows with missing groups
                    for idx, row in df[circuit_missing].iterrows():
                        dest = row[DNA_DESTINATION]
                        if dest in dest_to_group:
                            df.at[idx, TRANSFECTION_GROUP] = dest_to_group[dest]
        finally:
            # Clean up temporary key
            df.drop(columns=['_circuit_key'], inplace=True, errors='ignore')

    return df


def _infer_experiment_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Infer circuit names and transfection groups from destination columns.

    Args:
        df: Experiment design dataframe

    Returns:
        DataFrame with inferred metadata
    """
    if PLATE_DESTINATION in df.columns:
        df = infer_circuits(df)
    if DNA_DESTINATION in df.columns:
        df = infer_groups(df)
    return df


def _prepare_slot_configuration(layout_key: str, labware_config: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Prepare slot pools and tracking sets for layout generation.

    Args:
        layout_key: Layout type ('24tube' or '96well')
        labware_config: Optional labware configuration (unused, kept for compatibility)

    Returns:
        Dictionary containing:
            - layout: Layout configuration
            - reagent_slots: Reserved reagent positions
            - input_dna_slots: Available slots for DNA origins
            - working_slots: Available slots for dilutions/mixes
            - output_slots: Available output plate positions
    """
    layout = get_layout(layout_key)

    # Get reagent slots from static layout configuration
    reagent_slots = layout['reagent_slots']

    # Get slot pools
    slot_pools = get_layout_aware_slot_pools(layout_key, layout, reagent_slots)

    return {
        'layout': layout,
        'reagent_slots': reagent_slots,
        'input_dna_slots': slot_pools['input_dna_slots'],
        'working_slots': slot_pools['working_slots'],
        'output_slots': get_output_slots(layout['output_plates']),
    }


def _assign_all_slots(df: pd.DataFrame, layout_key: str, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Assign all slot types following the proper order to prevent conflicts.

    Assignment order:
    1. DNA sources (by DNA part) - from input pool
    2. DNA destinations (by Circuit/Group) - from working pool
    3. L3K/OM MM destinations (by Circuit/Group) - from working pool
    4. Dilution sources (by DNA part, conditional) - from working pool
    5. Plate destinations (by Circuit) - from output pool (separate)

    Args:
        df: Experiment dataframe
        layout_key: Layout type ('24tube' or '96well')
        config: Slot configuration

    Returns:
        DataFrame with all slots assigned
    """
    # Create slot assigner with global tracking
    assigner = SlotAssigner(layout_key, config)

    # Detect which rows need dilution
    needs_dilution = detect_dilutions(df)

    # Step 1: Assign DNA sources (input pool)
    df = assigner.assign_slots(
        df, DNA_ORIGIN, [DNA_PART_NAME],
        config['input_dna_slots'], is_output_pool=False
    )

    # Step 2: Assign DNA destinations (working pool)
    df = assigner.assign_slots(
        df, DNA_DESTINATION, [CIRCUIT_NAME, TRANSFECTION_GROUP],
        config['working_slots'], is_output_pool=False
    )

    # Step 3: Assign L3K/OM MM destinations (working pool)
    df = assigner.assign_slots(
        df, TRANSFECTION_DESTINATION, [CIRCUIT_NAME, TRANSFECTION_GROUP],
        config['working_slots'], is_output_pool=False
    )

    # Step 4: Assign dilution sources (working pool, conditional)
    df = assigner.assign_dilution_sources(
        df, needs_dilution, config['working_slots']
    )

    # Step 5: Assign plate destinations (output pool - separate tracking)
    df = assigner.assign_slots(
        df, PLATE_DESTINATION, [CIRCUIT_NAME],
        config['output_slots'], is_output_pool=True
    )

    return df


def generate_layout(df: pd.DataFrame, layout_key: str = '24tube', labware_config: Dict[str, str] = None) -> pd.DataFrame:
    """
    Generate complete layout with all slot assignments.

    Workflow:
        1. Infer missing metadata (circuit names, transfection groups)
        2. Prepare slot pools based on layout type
        3. Assign slots for DNA origins, dilutions, and destinations

    Args:
        df: Experiment design dataframe
        layout_key: Layout type ('24tube' or '96well')
        labware_config: Dictionary mapping slot numbers to labware types (for dynamic reagent slots)

    Returns:
        DataFrame with all slot assignments filled
    """
    df = df.copy()

    # Step 1: Infer experiment metadata
    df = _infer_experiment_metadata(df)

    # Step 2: Prepare slot configuration
    config = _prepare_slot_configuration(layout_key, labware_config)

    # Step 3: Assign all slots using layout-specific logic
    df = _assign_all_slots(df, layout_key, config)

    # Step 4: Fill transfection types
    df = fill_transfection_types(df)

    return df


def _fill_rack_layout(layout_data: Dict, df: pd.DataFrame, rack_idx: int, reagent_slots: List[str], reagent_labels: Dict[str, str] = None):
    """Helper to fill a rack layout with DNA sources, destinations, transfection destinations, and diluted sources."""
    if reagent_labels is None:
        reagent_labels = {}

    slot_fills = [
        (DNA_ORIGIN, lambda r: r[DNA_PART_NAME]),
        (DNA_DESTINATION, lambda r: f"{r[CIRCUIT_NAME]}-{r[TRANSFECTION_GROUP]}-DNA"),
        (TRANSFECTION_DESTINATION, lambda r: f"{r[CIRCUIT_NAME]}-{r[TRANSFECTION_GROUP]}-L3K"),
    ]

    # Add diluted sources if present
    if DILUTED_SOURCE in df.columns:
        slot_fills.append((DILUTED_SOURCE, lambda r: f"{r[DNA_PART_NAME]}-DILUTED"))

    for slot_col, label_fn in slot_fills:
        for _, row_data in df.iterrows():
            slot = row_data.get(slot_col, '')
            if slot and slot.endswith(f'.{rack_idx}'):
                pos = slot.split('.')[0]
                row_letter, col_num = pos[0], int(pos[1:]) - 1
                if layout_data[row_letter][col_num] == '':
                    layout_data[row_letter][col_num] = label_fn(row_data)

    # Mark reagent slots with specific labels
    for reagent_slot in reagent_slots:
        if reagent_slot.endswith(f'.{rack_idx}'):
            pos = reagent_slot.split('.')[0]
            row_letter, col_num = pos[0], int(pos[1:]) - 1
            if layout_data[row_letter][col_num] == '':
                # Use specific label if available, otherwise "Reserved"
                label = reagent_labels.get(reagent_slot, 'Reserved')
                layout_data[row_letter][col_num] = label


def generate_plate_layouts(df: pd.DataFrame, layout_key: str = '24tube', labware_config: Dict[str, str] = None) -> Dict[str, pd.DataFrame]:
    """
    Generate visual layouts for each rack/plate.

    Args:
        df: Experiment design dataframe with slot assignments
        layout_key: Layout type ('24tube' or '96well')
        labware_config: Dictionary mapping slot numbers to labware types (unused, kept for compatibility)

    Returns:
        Dictionary mapping layout names to DataFrames representing visual layouts
    """
    layouts = {}
    layout = get_layout(layout_key)

    # Get reagent slots and labels from static layout configuration
    reagent_slots = layout['reagent_slots']
    reagent_labels = layout.get('reagent_labels', {})

    # Input racks
    for rack_idx, rack in enumerate(layout['input_racks'], start=1):
        layout_data = {row: [''] * len(rack['cols']) for row in rack['rows']}
        _fill_rack_layout(layout_data, df, rack_idx, reagent_slots, reagent_labels)

        layout_df = pd.DataFrame(layout_data).T
        layout_df.columns = rack['cols']
        layouts[f'input_rack_{rack_idx}'] = layout_df

    # Output plates
    for plate_idx, output_plate in enumerate(layout['output_plates'], start=1):
        layout_data = {row: [''] * len(output_plate['cols']) for row in output_plate['rows']}

        for circuit in df[CIRCUIT_NAME].unique():
            circuit_rows = df[df[CIRCUIT_NAME] == circuit]
            if len(circuit_rows) > 0:
                output_well = circuit_rows[PLATE_DESTINATION].iloc[0]
                if output_well:
                    # Check if this well belongs to this plate (match sequential plate number)
                    well_parts = output_well.split('.')
                    well_plate_num = int(well_parts[1]) if len(well_parts) > 1 else 1

                    # Only add circuit if it belongs to this plate
                    if well_plate_num == plate_idx:
                        pos = well_parts[0]
                        row_letter, col_num = pos[0], int(pos[1:]) - 1
                        layout_data[row_letter][col_num] = circuit

        layout_df = pd.DataFrame(layout_data).T
        layout_df.columns = output_plate['cols']
        layouts[f'output_plate_{plate_idx}'] = layout_df

    return layouts
