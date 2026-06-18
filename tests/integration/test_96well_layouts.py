"""Integration tests specific to 96-well plate layouts."""

import pandas as pd
import pytest

from core.validation import validate_experiment_design
from core.layout import generate_layout
from core.config import (
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION,
    DILUTED_SOURCE,
)


class Test96WellPoolSeparation:
    """Test 96-well's strict pool separation between tubes and wells."""

    def test_dna_sources_only_from_tubes(self, labware_96well_minimal):
        """DNA sources must come from tube rack (rack 1), not well plates."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
        })

        result = generate_layout(df, '96well', labware_96well_minimal)

        # All DNA sources must be from slot 4 (tube rack)
        assert all('.1' in slot for slot in result[DNA_ORIGIN])
        assert all('.2' not in slot and '.3' not in slot for slot in result[DNA_ORIGIN])

    def test_dna_destinations_only_from_wells(self, labware_96well_minimal):
        """DNA destinations must come from well plates (racks 2-3), not tube rack."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, '96well', labware_96well_minimal)

        # All DNA destinations must be from slots 5-6 (well plates)
        assert all('.2' in slot or '.3' in slot for slot in result[DNA_DESTINATION])
        assert all('.1' not in slot for slot in result[DNA_DESTINATION])

    def test_transfection_destinations_only_from_wells(self, labware_96well_minimal):
        """L3K/OM MM destinations must come from well plates (racks 2-3)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, '96well', labware_96well_minimal)

        # All L3K destinations must be from slots 5-6
        assert all('.2' in slot or '.3' in slot for slot in result[TRANSFECTION_DESTINATION])
        assert all('.1' not in slot for slot in result[TRANSFECTION_DESTINATION])

    def test_diluted_sources_only_from_wells(self, labware_96well_minimal):
        """Diluted sources must come from well plates (racks 2-3), not tube rack."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['HighConc1', 'HighConc2'],
            CONCENTRATION: [500, 500],
            QUANTITY_DNA: [100, 100],  # Both need dilution
        })

        result = generate_layout(df, '96well', labware_96well_minimal)

        # All diluted sources must be from slot 6 (well plate)
        diluted_slots = result[DILUTED_SOURCE].dropna()
        diluted_slots = diluted_slots[diluted_slots != '']

        assert len(diluted_slots) == 2
        assert all('.3' in slot for slot in diluted_slots)
        assert all('.1' not in slot and '.2' not in slot for slot in diluted_slots)

    def test_manual_slot_respects_pool_separation(self, labware_96well_minimal):
        """Manual slot assignments that violate pool separation should be caught by validation."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_ORIGIN: ['A1.3'],  # INVALID: DNA source in well plate (slot 6)
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_minimal)
        assert not is_valid
        assert 'Layout Compatibility Errors' in error_msg
        assert 'must be in tube rack' in error_msg


class Test96WellMinimalConfig:
    """Test 96-well layouts with minimal configuration (1 tube rack, 1 well plate, 1 output)."""

    def test_minimal_single_circuit(self, labware_96well_minimal):
        """Single circuit with minimal 96-well config."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_minimal)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_minimal)

        # DNA sources from tube racks (racks 1 & 2)
        assert all('.1' in slot or '.2' in slot for slot in result[DNA_ORIGIN])

        # DNA destinations from well plate (rack 3, only well plate in minimal)
        assert all('.3' in slot for slot in result[DNA_DESTINATION])

        # Plate destination from output plate (plate 1)
        assert all('.1' in slot for slot in result[PLATE_DESTINATION])

    def test_minimal_capacity_limits(self, labware_96well_minimal):
        """Test behavior approaching capacity limits with minimal config."""
        # Tube rack has 24 positions, well plate has 96 positions
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 15,
            TRANSFECTION_GROUP: ['X1'] * 15,
            DNA_PART_NAME: [f'Part{i}' for i in range(15)],
            CONCENTRATION: [50] * 15,
            QUANTITY_DNA: [50] * 15,  # 15 * 50 = 750ng (under 800ng limit)
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_minimal)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_minimal)

        # All 15 parts should get unique DNA sources from tube rack
        assert len(result[DNA_ORIGIN].unique()) == 15


class Test96WellFullConfig:
    """Test 96-well layouts with full configuration (1 tube rack, 2 well plates, 2 outputs)."""

    def test_full_config_multiple_circuits(self, labware_96well_full):
        """Multiple circuits utilizing full configuration."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 6 + ['Circuit2'] * 6 + ['Circuit3'] * 6,
            TRANSFECTION_GROUP: ['X1'] * 6 + ['X1'] * 6 + ['X1'] * 6,
            DNA_PART_NAME: [f'Part{i}' for i in range(18)],
            CONCENTRATION: [50] * 18,
            QUANTITY_DNA: [100] * 18,
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_full)

        # DNA sources should all be from tube rack (rack 1)
        assert all('.1' in slot for slot in result[DNA_ORIGIN])

        # DNA destinations should span across well plates (racks 2-3)
        dna_dest_slots = set(slot.split('.')[1] for slot in result[DNA_DESTINATION])
        assert '2' in dna_dest_slots or '3' in dna_dest_slots

        # Circuits should use different output plates
        plate_dests_by_circuit = result.groupby(CIRCUIT_NAME)[PLATE_DESTINATION].first()
        assert len(plate_dests_by_circuit.unique()) == 3

    def test_full_config_with_multiple_groups(self, labware_96well_full):
        """Test multiple transfection groups with full 96-well configuration."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 8,
            TRANSFECTION_GROUP: ['X1'] * 4 + ['X2'] * 4,
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'] * 2,  # Same parts in both groups
            CONCENTRATION: [50] * 8,
            QUANTITY_DNA: [100] * 8,
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_full)

        # Same DNA parts should share sources across groups (from tube rack)
        for part in ['mKO2', 'mNG', 'Csy4', 'PacBlue']:
            part_rows = result[result[DNA_PART_NAME] == part]
            assert len(part_rows[DNA_ORIGIN].unique()) == 1

        # Different groups should have different DNA destinations (in well plates)
        x1_dest = result[result[TRANSFECTION_GROUP] == 'X1'][DNA_DESTINATION].iloc[0]
        x2_dest = result[result[TRANSFECTION_GROUP] == 'X2'][DNA_DESTINATION].iloc[0]
        assert x1_dest != x2_dest

        # All should share same plate destination (same circuit)
        assert len(result[PLATE_DESTINATION].unique()) == 1


class Test96WellDilutionHandling:
    """Test dilution handling in 96-well layouts."""

    def test_dilution_from_well_plates_only(self, labware_96well_full):
        """Diluted sources must come from well plates, not tube rack."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['HighConc1', 'HighConc2', 'HighConc3'],
            CONCENTRATION: [500, 400, 600],
            QUANTITY_DNA: [100, 100, 100],  # All need dilution
        })

        result = generate_layout(df, '96well', labware_96well_full)

        # All should have diluted sources from well plates
        diluted_slots = result[DILUTED_SOURCE].dropna()
        diluted_slots = diluted_slots[diluted_slots != '']

        assert len(diluted_slots) == 3
        assert all('.2' in slot or '.3' in slot for slot in diluted_slots)
        assert all('.1' not in slot for slot in diluted_slots)

    def test_same_part_shares_diluted_source_across_groups(self, labware_96well_full):
        """Same DNA part needing dilution should share diluted source across groups."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['HighConc', 'HighConc'],  # Same part
            CONCENTRATION: [500, 500],
            QUANTITY_DNA: [100, 100],  # Both need dilution
        })

        result = generate_layout(df, '96well', labware_96well_full)

        # Both should share same diluted source
        assert result.iloc[0][DILUTED_SOURCE] == result.iloc[1][DILUTED_SOURCE]
        assert pd.notna(result.iloc[0][DILUTED_SOURCE])


class Test96WellScalability:
    """Test 96-well layout scalability with larger datasets."""

    def test_large_number_of_dna_parts(self, labware_96well_full):
        """Test with many DNA parts (tube rack has 24 positions)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 15,
            TRANSFECTION_GROUP: ['X1'] * 15,
            DNA_PART_NAME: [f'Part{i}' for i in range(15)],
            CONCENTRATION: [50] * 15,
            QUANTITY_DNA: [50] * 15,  # 15 * 50 = 750ng (under limit)
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid, f"Validation failed: {error_msg}"

        result = generate_layout(df, '96well', labware_96well_full)

        # All 15 parts should get unique DNA sources from tube rack
        assert len(result[DNA_ORIGIN].unique()) == 15
        # All from rack 1
        assert all('.1' in slot for slot in result[DNA_ORIGIN])

    def test_many_transfection_groups(self, labware_96well_full):
        """Test with many transfection groups (utilizing well plate capacity)."""
        # Create 20 different groups, each with 2 DNA parts
        circuits = ['Circuit1'] * 20 + ['Circuit2'] * 20
        groups = [f'X{i}' for i in range(1, 21)] * 2
        parts = ['mKO2', 'mNG'] * 20

        df = pd.DataFrame({
            CIRCUIT_NAME: circuits,
            TRANSFECTION_GROUP: groups,
            DNA_PART_NAME: parts,
            CONCENTRATION: [50] * 40,
            QUANTITY_DNA: [20] * 40,  # Each circuit: 20 groups * 2 parts * 20ng = 800ng (at limit)
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_full)

        # Each group should have unique DNA destination
        unique_groups = result[[CIRCUIT_NAME, TRANSFECTION_GROUP]].drop_duplicates()
        dna_dests_by_group = []
        for _, row in unique_groups.iterrows():
            group_rows = result[
                (result[CIRCUIT_NAME] == row[CIRCUIT_NAME]) &
                (result[TRANSFECTION_GROUP] == row[TRANSFECTION_GROUP])
            ]
            dna_dests_by_group.append(group_rows[DNA_DESTINATION].iloc[0])

        # All groups should have unique DNA destinations
        assert len(set(dna_dests_by_group)) == len(dna_dests_by_group)

        # All DNA destinations from well plates
        assert all('.2' in slot or '.3' in slot for slot in dna_dests_by_group)


class Test96WellReagentSlotAvoidance:
    """Test that 96-well layouts avoid reagent slots."""

    def test_reagent_slots_not_used(self, labware_96well_full):
        """Verify reagent slots are not used for DNA/destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 10,
            TRANSFECTION_GROUP: ['X1'] * 5 + ['X2'] * 5,
            DNA_PART_NAME: [f'Part{i}' for i in range(10)],
            CONCENTRATION: [50] * 10,
            QUANTITY_DNA: [100] * 10,
        })

        result = generate_layout(df, '96well', labware_96well_full)

        # Collect all assigned slots
        all_slots = []
        for col in [DNA_ORIGIN, DNA_DESTINATION, TRANSFECTION_DESTINATION, DILUTED_SOURCE]:
            slots = result[col].dropna()
            slots = slots[slots != '']
            all_slots.extend(slots.tolist())

        # Get reagent slots from layout config
        from core.config import get_layout
        layout = get_layout('96well')
        reagent_slots = set(layout['reagent_slots'])

        # No assigned slot should be a reagent slot
        for slot in all_slots:
            assert slot not in reagent_slots, f"Slot {slot} is a reserved reagent slot"


class Test96WellManualAssignments:
    """Test preservation of manual slot assignments in 96-well layouts."""

    def test_manual_dna_source_in_tube_rack(self, labware_96well_full):
        """Manual DNA sources in tube rack should be preserved."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['Part1', 'Part2'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.1', ''],  # Manual assignment in tube rack
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_full)

        # Manual assignment preserved
        assert result.iloc[0][DNA_ORIGIN] == 'A1.1'
        # Auto-assignment also from tube rack
        assert '.1' in result.iloc[1][DNA_ORIGIN]

    def test_manual_dna_dest_in_well_plate(self, labware_96well_full):
        """Manual DNA destinations in well plates should be preserved."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['Part1', 'Part2'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_DESTINATION: ['', 'H12.3'],  # Manual assignment in well plate
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_full)

        # Manual assignment preserved
        assert result.iloc[1][DNA_DESTINATION] == 'H12.3'
        # Auto-assignment also from well plate (slot 6)
        assert '.3' in result.iloc[0][DNA_DESTINATION]

    def test_mixed_manual_auto_assignments(self, labware_96well_full):
        """Mix of manual and auto assignments across different columns."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['Part1', 'Part2'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.1', 'B2.1'],  # Manual for both
            DNA_DESTINATION: ['C3.3', ''],  # Manual for first (slot 6 - well plate), auto for second
            PLATE_DESTINATION: ['', 'A1.2'],  # Auto for first, manual for second
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_full)
        assert is_valid

        result = generate_layout(df, '96well', labware_96well_full)

        # Manual assignments preserved
        assert result.iloc[0][DNA_ORIGIN] == 'A1.1'
        assert result.iloc[1][DNA_ORIGIN] == 'B2.1'
        assert result.iloc[0][DNA_DESTINATION] == 'C3.3'

        # Auto-assignment for second DNA destination (from well plate - slot 6 only)
        assert pd.notna(result.iloc[1][DNA_DESTINATION])
        assert '.3' in result.iloc[1][DNA_DESTINATION]

        # Both should share same plate destination (same circuit)
        assert result.iloc[0][PLATE_DESTINATION] == result.iloc[1][PLATE_DESTINATION]
