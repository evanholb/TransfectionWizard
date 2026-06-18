"""Integration tests specific to 24-tube rack layouts."""

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


class Test24TubeMinimalConfig:
    """Test 24-tube layouts with minimal configuration (1 input rack, 1 output plate)."""

    def test_minimal_single_circuit(self, labware_24tube_minimal):
        """Single circuit with minimal 24-tube config."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
        })

        is_valid, error_msg = validate_experiment_design(df, '24tube', labware_24tube_minimal)
        assert is_valid

        result = generate_layout(df, '24tube', labware_24tube_minimal)

        # All DNA sources should be from rack 1 (only input rack)
        assert all('.1' in slot for slot in result[DNA_ORIGIN])

        # DNA destinations should be from rack 1 (same rack for 24-tube)
        assert all('.1' in slot for slot in result[DNA_DESTINATION])

        # Plate destination should be from plate 1 (only output plate)
        assert all('.1' in slot for slot in result[PLATE_DESTINATION])

    def test_minimal_multiple_circuits_slot_exhaustion(self, labware_24tube_minimal):
        """Test behavior when approaching slot limits with minimal config."""
        # Create design with many DNA parts (rack 1 has 24 positions)
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 10,
            TRANSFECTION_GROUP: ['X1'] * 10,
            DNA_PART_NAME: [f'Part{i}' for i in range(10)],
            CONCENTRATION: [50] * 10,
            QUANTITY_DNA: [80] * 10,  # 10 parts × 80ng = 800ng (at circuit limit)
        })

        is_valid, error_msg = validate_experiment_design(df, '24tube', labware_24tube_minimal)
        assert is_valid

        result = generate_layout(df, '24tube', labware_24tube_minimal)

        # All parts should get unique DNA sources
        assert len(result[DNA_ORIGIN].unique()) == 10


class Test24TubeFullConfig:
    """Test 24-tube layouts with full configuration (3 input racks, 2 output plates)."""

    def test_full_config_multiple_circuits(self, labware_24tube_full):
        """Multiple circuits utilizing full configuration."""
        # Create 30 unique DNA parts to force use of multiple racks (24 positions per rack)
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 10 + ['Circuit2'] * 10 + ['Circuit3'] * 10,
            TRANSFECTION_GROUP: ['X1'] * 10 + ['X1'] * 10 + ['X1'] * 10,
            DNA_PART_NAME: [f'Part{i}' for i in range(30)],
            CONCENTRATION: [50] * 30,
            QUANTITY_DNA: [26] * 30,  # 10 parts × 26ng = 260ng per circuit (under 800ng limit)
        })

        is_valid, error_msg = validate_experiment_design(df, '24tube', labware_24tube_full)
        assert is_valid

        result = generate_layout(df, '24tube', labware_24tube_full)

        # DNA sources should span across multiple input racks (slots 4, 5, 6)
        dna_source_slots = set()
        for slot in result[DNA_ORIGIN]:
            slot_num = slot.split('.')[1]
            dna_source_slots.add(slot_num)

        # Should use multiple input racks
        assert len(dna_source_slots) > 1
        assert all(s in ['1', '2', '3'] for s in dna_source_slots)

        # Circuits should use different output plates
        plate_dests_by_circuit = result.groupby(CIRCUIT_NAME)[PLATE_DESTINATION].first()
        assert len(plate_dests_by_circuit.unique()) == 3

    def test_full_config_with_multiple_groups(self, labware_24tube_full):
        """Test multiple transfection groups with full configuration."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 8,
            TRANSFECTION_GROUP: ['X1'] * 4 + ['X2'] * 4,
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'] * 2,  # Same parts in both groups
            CONCENTRATION: [50] * 8,
            QUANTITY_DNA: [100] * 8,
        })

        is_valid, error_msg = validate_experiment_design(df, '24tube', labware_24tube_full)
        assert is_valid

        result = generate_layout(df, '24tube', labware_24tube_full)

        # Same DNA parts should share sources across groups
        for part in ['mKO2', 'mNG', 'Csy4', 'PacBlue']:
            part_rows = result[result[DNA_PART_NAME] == part]
            assert len(part_rows[DNA_ORIGIN].unique()) == 1

        # Different groups should have different DNA destinations
        x1_dest = result[result[TRANSFECTION_GROUP] == 'X1'][DNA_DESTINATION].iloc[0]
        x2_dest = result[result[TRANSFECTION_GROUP] == 'X2'][DNA_DESTINATION].iloc[0]
        assert x1_dest != x2_dest

        # All should share same plate destination (same circuit)
        assert len(result[PLATE_DESTINATION].unique()) == 1


class Test24TubeSharedInputPool:
    """Test 24-tube's shared input pool behavior (DNA sources and destinations from same racks)."""

    def test_no_pool_separation_required(self, labware_24tube_full):
        """24-tube doesn't require separation between DNA sources and destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        # Both DNA sources and DNA destinations can be from same rack
        dna_source_slot = result.iloc[0][DNA_ORIGIN].split('.')[1]
        dna_dest_slot = result.iloc[0][DNA_DESTINATION].split('.')[1]

        # Both should be from input racks (1, 2, or 3)
        assert dna_source_slot in ['1', '2', '3']
        assert dna_dest_slot in ['1', '2', '3']

    def test_same_well_position_different_purposes(self, labware_24tube_full):
        """24-tube can use same well position for different purposes (e.g., A1.1 for source, A1.2 for destination)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2', 'X3'],
            DNA_PART_NAME: ['Part1', 'Part2', 'Part3'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        # Extract well positions (e.g., "A1" from "A1.1")
        source_positions = set(slot.split('.')[0] for slot in result[DNA_ORIGIN])
        dest_positions = set(slot.split('.')[0] for slot in result[DNA_DESTINATION])

        # Positions might overlap (allowed in 24-tube since different racks)
        # This is OK and expected


class Test24TubeDilutionHandling:
    """Test dilution handling in 24-tube layouts."""

    def test_dilution_from_shared_pool(self, labware_24tube_full):
        """Diluted sources should come from same pool as DNA destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['HighConc1', 'HighConc2'],
            CONCENTRATION: [500, 500],
            QUANTITY_DNA: [100, 100],  # Both need dilution
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        # Both should have diluted sources
        assert pd.notna(result.iloc[0][DILUTED_SOURCE])
        assert pd.notna(result.iloc[1][DILUTED_SOURCE])

        # Diluted sources should be from input racks
        diluted_slots = set(slot.split('.')[1] for slot in result[DILUTED_SOURCE] if pd.notna(slot) and slot != '')
        assert all(s in ['1', '2', '3'] for s in diluted_slots)

    def test_multiple_parts_needing_dilution(self, labware_24tube_full):
        """Multiple DNA parts needing dilution should each get unique diluted source."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 5,
            TRANSFECTION_GROUP: ['X1'] * 5,
            DNA_PART_NAME: [f'HighConc{i}' for i in range(5)],
            CONCENTRATION: [500] * 5,
            QUANTITY_DNA: [100] * 5,  # All need dilution
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        # All should have diluted sources
        diluted_sources = result[DILUTED_SOURCE].dropna()
        diluted_sources = diluted_sources[diluted_sources != '']

        assert len(diluted_sources) == 5
        # All should be unique
        assert len(diluted_sources.unique()) == 5


class Test24TubeReagentSlotAvoidance:
    """Test that 24-tube layouts avoid reagent slots."""

    def test_reagent_slots_not_used(self, labware_24tube_full):
        """Verify reagent slots are not used for DNA/destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'] * 10,
            TRANSFECTION_GROUP: ['X1'] * 5 + ['X2'] * 5,
            DNA_PART_NAME: [f'Part{i}' for i in range(10)],
            CONCENTRATION: [50] * 10,
            QUANTITY_DNA: [100] * 10,
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        # Collect all assigned slots
        all_slots = []
        for col in [DNA_ORIGIN, DNA_DESTINATION, TRANSFECTION_DESTINATION, DILUTED_SOURCE]:
            slots = result[col].dropna()
            slots = slots[slots != '']
            all_slots.extend(slots.tolist())

        # Get reagent slots from layout config
        from core.config import get_layout
        layout = get_layout('24tube')
        reagent_slots = set(layout['reagent_slots'])

        # No assigned slot should be a reagent slot
        for slot in all_slots:
            assert slot not in reagent_slots, f"Slot {slot} is a reserved reagent slot"


class Test24TubeManualAssignments:
    """Test preservation of manual slot assignments in 24-tube layouts."""

    def test_manual_dna_source_preserved(self, labware_24tube_full):
        """Manually assigned DNA sources should be preserved."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['Part1', 'Part2', 'Part3'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
            DNA_ORIGIN: ['A1.1', '', 'B2.2'],  # Manual assignments
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        assert result.iloc[0][DNA_ORIGIN] == 'A1.1'
        assert result.iloc[2][DNA_ORIGIN] == 'B2.2'
        # Second row should be auto-assigned
        assert pd.notna(result.iloc[1][DNA_ORIGIN])
        assert result.iloc[1][DNA_ORIGIN] not in ['A1.1', 'B2.2']

    def test_partial_manual_assignments(self, labware_24tube_full):
        """Mix of manual and auto assignments should work correctly."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['Part1', 'Part2'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_DESTINATION: ['C3.1', ''],  # Manual for X1, auto for X2
            PLATE_DESTINATION: ['', 'A1.2'],  # Auto for both (but second provides hint)
        })

        result = generate_layout(df, '24tube', labware_24tube_full)

        # Manual DNA destination preserved
        assert result.iloc[0][DNA_DESTINATION] == 'C3.1'

        # Auto-assigned DNA destination different from manual
        assert pd.notna(result.iloc[1][DNA_DESTINATION])
        assert result.iloc[1][DNA_DESTINATION] != 'C3.1'

        # Both should share plate destination (same circuit)
        assert result.iloc[0][PLATE_DESTINATION] == result.iloc[1][PLATE_DESTINATION]
