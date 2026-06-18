"""Tests for slot assignment algorithms."""

import pandas as pd
import pytest

from core.layout import (
    generate_layout,
    get_layout_aware_slot_pools,
)
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
    get_layout,
)


class TestDNASourceAssignment:
    """Test DNA source slot assignment."""

    def test_same_dna_part_gets_same_slot(self):
        """Same DNA part across different groups should share one DNA source slot."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mKO2'],  # Same part
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Both rows should have same DNA source
        assert result.iloc[0][DNA_ORIGIN] == result.iloc[1][DNA_ORIGIN]
        assert pd.notna(result.iloc[0][DNA_ORIGIN])

    def test_different_dna_parts_get_different_slots(self):
        """Different DNA parts should get different DNA source slots."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],  # Different parts
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Different parts should have different slots
        assert result.iloc[0][DNA_ORIGIN] != result.iloc[1][DNA_ORIGIN]
        assert pd.notna(result.iloc[0][DNA_ORIGIN])
        assert pd.notna(result.iloc[1][DNA_ORIGIN])

    def test_preserves_existing_dna_source(self):
        """Manually assigned DNA source slots should be preserved."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.4', ''],  # Manual assignment for mKO2
        })

        result = generate_layout(df, layout_key='24tube')

        # Manual assignment preserved
        assert result.iloc[0][DNA_ORIGIN] == 'A1.4'
        # Auto-assignment for second part
        assert pd.notna(result.iloc[1][DNA_ORIGIN])
        assert result.iloc[1][DNA_ORIGIN] != 'A1.4'

    def test_96well_dna_sources_from_tube_rack(self, labware_96well_minimal):
        """96-well: DNA sources must come from tube rack (rack 1)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='96well', labware_config=labware_96well_minimal)

        # Both should be from rack 1 (tube rack)
        assert '.1' in result.iloc[0][DNA_ORIGIN]
        assert '.1' in result.iloc[1][DNA_ORIGIN]


class TestDNADestinationAssignment:
    """Test DNA destination slot assignment."""

    def test_same_circuit_group_gets_same_slot(self):
        """Same Circuit/Group combo should share DNA destination."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],  # Different parts, same group
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Same Circuit/Group should share DNA destination
        assert result.iloc[0][DNA_DESTINATION] == result.iloc[1][DNA_DESTINATION]
        assert pd.notna(result.iloc[0][DNA_DESTINATION])

    def test_different_groups_get_different_slots(self):
        """Different Circuit/Group combos should get different DNA destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Different groups should have different DNA destinations
        assert result.iloc[0][DNA_DESTINATION] != result.iloc[1][DNA_DESTINATION]
        assert pd.notna(result.iloc[0][DNA_DESTINATION])
        assert pd.notna(result.iloc[1][DNA_DESTINATION])

    def test_96well_dna_dest_from_well_plates(self, labware_96well_minimal):
        """96-well: DNA destinations must come from well plates (racks 2-3)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='96well', labware_config=labware_96well_minimal)

        # Both should be from racks 2 or 3 (well plates)
        assert '.2' in result.iloc[0][DNA_DESTINATION] or '.3' in result.iloc[0][DNA_DESTINATION]
        assert '.2' in result.iloc[1][DNA_DESTINATION] or '.3' in result.iloc[1][DNA_DESTINATION]


class TestTransfectionDestinationAssignment:
    """Test Lipofectamine/OM MM destination slot assignment."""

    def test_same_circuit_group_gets_same_slot(self):
        """Same Circuit/Group should share L3K destination."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Same Circuit/Group should share L3K destination
        assert result.iloc[0][TRANSFECTION_DESTINATION] == result.iloc[1][TRANSFECTION_DESTINATION]
        assert pd.notna(result.iloc[0][TRANSFECTION_DESTINATION])

    def test_different_groups_get_different_slots(self):
        """Different Circuit/Group combos should get different L3K destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Different groups should have different L3K destinations
        assert result.iloc[0][TRANSFECTION_DESTINATION] != result.iloc[1][TRANSFECTION_DESTINATION]
        assert pd.notna(result.iloc[0][TRANSFECTION_DESTINATION])
        assert pd.notna(result.iloc[1][TRANSFECTION_DESTINATION])


class TestPlateDestinationAssignment:
    """Test output plate destination slot assignment."""

    def test_same_circuit_gets_same_slot(self):
        """Same Circuit (regardless of group) should share plate destination."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Same Circuit should share plate destination
        assert result.iloc[0][PLATE_DESTINATION] == result.iloc[1][PLATE_DESTINATION]
        assert pd.notna(result.iloc[0][PLATE_DESTINATION])

    def test_different_circuits_get_different_slots(self):
        """Different Circuits should get different plate destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit2'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Different circuits should have different plate destinations
        assert result.iloc[0][PLATE_DESTINATION] != result.iloc[1][PLATE_DESTINATION]
        assert pd.notna(result.iloc[0][PLATE_DESTINATION])
        assert pd.notna(result.iloc[1][PLATE_DESTINATION])

    def test_plate_dest_from_output_slots(self, labware_24tube_minimal):
        """Plate destinations should come from output plates (plate 1)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
        })

        result = generate_layout(df, layout_key='24tube', labware_config=labware_24tube_minimal)

        # Should be from plate 1 (only output plate in minimal config)
        assert '.1' in result.iloc[0][PLATE_DESTINATION]


class TestDilutedSourceAssignment:
    """Test diluted source slot assignment."""

    def test_dilution_needed_assigns_slot(self):
        """DNA requiring dilution should get diluted source slot."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [100],
            QUANTITY_DNA: [150],  # 150 < 200, needs dilution
        })

        result = generate_layout(df, layout_key='24tube')

        # Should have diluted source assigned
        assert pd.notna(result.iloc[0][DILUTED_SOURCE])
        assert result.iloc[0][DILUTED_SOURCE] != ''

    def test_no_dilution_needed_no_slot(self):
        """DNA not requiring dilution should not get diluted source slot."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [200],  # 200 >= 100, no dilution
        })

        result = generate_layout(df, layout_key='24tube')

        # Should not have diluted source
        assert pd.isna(result.iloc[0][DILUTED_SOURCE]) or result.iloc[0][DILUTED_SOURCE] == ''

    def test_same_dna_part_shares_diluted_source(self):
        """Same DNA part needing dilution should share diluted source slot."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mKO2'],  # Same part
            CONCENTRATION: [100, 100],
            QUANTITY_DNA: [150, 150],  # Both need dilution
        })

        result = generate_layout(df, layout_key='24tube')

        # Both should share same diluted source
        assert result.iloc[0][DILUTED_SOURCE] == result.iloc[1][DILUTED_SOURCE]
        assert pd.notna(result.iloc[0][DILUTED_SOURCE])

    def test_different_parts_get_different_diluted_sources(self):
        """Different DNA parts needing dilution should get different diluted sources."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],  # Different parts
            CONCENTRATION: [100, 100],
            QUANTITY_DNA: [150, 150],  # Both need dilution
        })

        result = generate_layout(df, layout_key='24tube')

        # Different parts should have different diluted sources
        assert result.iloc[0][DILUTED_SOURCE] != result.iloc[1][DILUTED_SOURCE]
        assert pd.notna(result.iloc[0][DILUTED_SOURCE])
        assert pd.notna(result.iloc[1][DILUTED_SOURCE])

    def test_96well_dilution_from_well_plates(self, labware_96well_minimal):
        """96-well: Diluted sources must come from well plates (racks 2-3)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [100],
            QUANTITY_DNA: [150],  # Needs dilution
        })

        result = generate_layout(df, layout_key='96well', labware_config=labware_96well_minimal)

        # Should be from well plates (racks 2-3)
        diluted = result.iloc[0][DILUTED_SOURCE]
        assert pd.notna(diluted)
        assert '.2' in diluted or '.3' in diluted

    def test_preserves_manual_diluted_source(self):
        """Manually assigned diluted sources should be preserved."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [100, 100],
            QUANTITY_DNA: [150, 150],  # Both need dilution
            DILUTED_SOURCE: ['B3.4', ''],  # Manual assignment for mKO2
        })

        result = generate_layout(df, layout_key='24tube')

        # Manual assignment preserved
        assert result.iloc[0][DILUTED_SOURCE] == 'B3.4'
        # Auto-assignment for second part
        assert pd.notna(result.iloc[1][DILUTED_SOURCE])
        assert result.iloc[1][DILUTED_SOURCE] != 'B3.4'


class TestGlobalSlotTracking:
    """Test that slot assignment avoids conflicts across all columns."""

    def test_no_slot_reuse_across_input_columns(self):
        """Same slot should not be used in different input columns."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Collect all slots from input columns
        all_slots = []
        for col in [DNA_ORIGIN, DNA_DESTINATION, TRANSFECTION_DESTINATION]:
            for slot in result[col]:
                if pd.notna(slot) and slot != '':
                    all_slots.append(slot)

        # Should be no duplicates
        # Note: DNA_ORIGIN has 3 unique parts, DNA_DESTINATION has 1 (same group), TRANSFECTION_DESTINATION has 1 (same group)
        # So we expect: 3 DNA sources + 1 DNA dest + 1 L3K dest = 5 unique slots
        unique_slots = set(all_slots)
        assert len(unique_slots) == 5, f"Expected 5 unique slots, got {len(unique_slots)}: {unique_slots}"

    def test_output_slots_separate_from_input(self):
        """Plate destinations can reuse well positions from input slots."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
        })

        result = generate_layout(df, layout_key='24tube')

        # Even if same well position (e.g., A1), different slot numbers mean different physical locations
        # This is allowed and expected
        assert pd.notna(result.iloc[0][PLATE_DESTINATION])


class TestLayoutAwareSlotPools:
    """Test layout-aware slot pool generation."""

    def test_24tube_shared_pools(self):
        """24-tube: DNA sources and working slots share same pool."""
        layout = get_layout('24tube')
        reagent_slots = layout['reagent_slots']

        pools = get_layout_aware_slot_pools('24tube', layout, reagent_slots)

        # Should be the same pool
        assert pools['input_dna_slots'] == pools['working_slots']
        assert len(pools['input_dna_slots']) > 0

    def test_96well_separate_pools(self):
        """96-well: DNA sources (tubes) and working slots (wells) are separate."""
        layout = get_layout('96well')
        reagent_slots = layout['reagent_slots']

        pools = get_layout_aware_slot_pools('96well', layout, reagent_slots)

        # Input DNA slots should only be from racks 1 & 2 (tube racks)
        assert all('.1' in slot or '.2' in slot for slot in pools['input_dna_slots'])

        # Working slots should only be from rack 3 (well plate)
        assert all('.3' in slot for slot in pools['working_slots'])

        # Should be non-overlapping
        assert set(pools['input_dna_slots']).isdisjoint(set(pools['working_slots']))
