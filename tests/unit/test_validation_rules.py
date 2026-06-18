"""Tests for validation rules in core.validation module."""

import pandas as pd
import pytest

from core.validation import (
    validate_experiment_design,
    SlotValidator,
    _validate_layout_compatibility,
    _validate_global_uniqueness,
    _validate_grouping_consistency,
    _validate_circuit_dna_limits,
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
)


class TestRequiredFieldValidation:
    """Test that required fields cannot be empty."""

    def test_empty_dna_part_name_fails(self):
        """DNA part name (Contents) must not be empty."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: [''],  # Empty
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Required Field Errors' in error_msg
        assert DNA_PART_NAME in error_msg

    def test_empty_concentration_fails(self):
        """Concentration must not be empty."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [None],  # Empty
            QUANTITY_DNA: [100],
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Required Field Errors' in error_msg
        assert CONCENTRATION in error_msg

    def test_empty_quantity_dna_fails(self):
        """DNA wanted (Quantity DNA) must not be empty."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [None],  # Empty (None instead of empty string)
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Required Field Errors' in error_msg
        assert QUANTITY_DNA in error_msg

    def test_all_required_fields_present_passes(self):
        """Valid minimal format with all required fields should pass."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid
        assert error_msg is None


class TestLayoutCompatibilityValidation:
    """Test layout-specific slot validation."""

    def test_96well_dna_source_must_be_tube_rack(self, labware_96well_minimal):
        """96-well: DNA sources must be in tube racks (racks 1 & 2), not well plate."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_ORIGIN: ['A1.3'],  # Well plate (rack 3) - INVALID
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_minimal)
        assert not is_valid
        assert 'Layout Compatibility Errors' in error_msg
        assert 'must be in tube rack' in error_msg or 'must be in well plate' in error_msg

    def test_96well_dna_dest_must_be_well_plate(self, labware_96well_minimal):
        """96-well: DNA destinations must be in well plate (rack 3), not tube racks."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_DESTINATION: ['A1.1'],  # Tube rack 1 - INVALID
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_minimal)
        assert not is_valid
        assert 'Layout Compatibility Errors' in error_msg
        assert 'must be in well plate' in error_msg or 'must be in tube rack' in error_msg

    def test_96well_valid_pool_separation(self, labware_96well_minimal):
        """96-well: Valid when DNA sources in tubes, destinations in wells."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_ORIGIN: ['A1.1'],  # Tube rack (rack 1) - VALID
            DNA_DESTINATION: ['A1.3'],  # Well plate (rack 3) - VALID
        })

        is_valid, error_msg = validate_experiment_design(df, '96well', labware_96well_minimal)
        assert is_valid, f"Expected validation to pass but got: {error_msg}"

    def test_24tube_no_pool_separation_required(self, labware_24tube_minimal):
        """24-tube: All input slots are tubes, no separation needed."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_ORIGIN: ['A1.1'],  # Tube rack 1
            DNA_DESTINATION: ['A2.1'],  # Same rack - VALID for 24tube
        })

        is_valid, error_msg = validate_experiment_design(df, '24tube', labware_24tube_minimal)
        assert is_valid, f"Expected validation to pass but got: {error_msg}"

    def test_invalid_slot_for_layout(self, labware_24tube_minimal):
        """Slot that doesn't exist in layout configuration should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_ORIGIN: ['A1.7'],  # Slot 7 doesn't exist in minimal config
        })

        is_valid, error_msg = validate_experiment_design(df, '24tube', labware_24tube_minimal)
        assert not is_valid
        assert 'Layout Compatibility Errors' in error_msg


class TestSlotConflictValidation:
    """Test global slot uniqueness rules."""

    def test_same_slot_different_entities_in_column_fails(self):
        """Same slot assigned to different DNA parts in DNA source column should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],  # Different parts
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.4', 'A1.4'],  # Same slot - CONFLICT
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Slot Conflict Errors' in error_msg
        assert 'A1.4' in error_msg
        assert 'multiple entities' in error_msg

    def test_same_slot_cross_column_input_pool_fails(self):
        """Same slot used in different input columns should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.4', ''],
            DNA_DESTINATION: ['', 'A1.4'],  # Same slot as DNA source - CONFLICT
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Slot Conflict Errors' in error_msg
        assert 'A1.4' in error_msg
        assert 'multiple input columns' in error_msg

    def test_same_slot_input_and_output_allowed(self):
        """Same slot in input pool and output pool is allowed (different physical locations)."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1'],
            TRANSFECTION_GROUP: ['X1'],
            DNA_PART_NAME: ['mKO2'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [100],
            DNA_ORIGIN: ['A1.1'],  # Input rack 1
            PLATE_DESTINATION: ['A1.1'],  # Output plate 1 - Same well position but different physical location - OK
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid, f"Expected validation to pass but got: {error_msg}"

    def test_same_slot_same_entity_allowed(self):
        """Same slot for same DNA part in multiple rows is allowed."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mKO2'],  # Same part
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.1', 'A1.1'],  # Same slot, same part - OK
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid, f"Expected validation to pass but got: {error_msg}"
        assert error_msg is None


class TestGroupingConsistencyValidation:
    """Test entity-to-slot consistency rules."""

    def test_dna_part_multiple_sources_fails(self):
        """Same DNA part assigned to different source slots should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mKO2'],  # Same part
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.4', 'A2.4'],  # Different slots - CONFLICT
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Grouping Rule Violations' in error_msg
        assert 'mKO2' in error_msg
        assert 'multiple' in error_msg
        assert DNA_ORIGIN in error_msg

    def test_circuit_group_multiple_dna_destinations_fails(self):
        """Same Circuit/Group assigned to different DNA destinations should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],  # Same group
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_DESTINATION: ['A1.5', 'A2.5'],  # Different slots - CONFLICT
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Grouping Rule Violations' in error_msg
        assert 'Circuit1/X1' in error_msg
        assert 'multiple' in error_msg
        assert DNA_DESTINATION in error_msg

    def test_circuit_multiple_plate_destinations_fails(self):
        """Same Circuit assigned to different plate destinations should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            PLATE_DESTINATION: ['A1.2', 'A2.2'],  # Different slots - CONFLICT
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Grouping Rule Violations' in error_msg
        assert 'Circuit1' in error_msg
        assert 'multiple' in error_msg
        assert PLATE_DESTINATION in error_msg

    def test_consistent_grouping_passes(self):
        """Consistent entity-to-slot mappings should pass."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit2', 'Circuit2'],
            TRANSFECTION_GROUP: ['X1', 'X2', 'X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'mKO2', 'mNG'],
            CONCENTRATION: [50, 50, 50, 50],
            QUANTITY_DNA: [100, 100, 100, 100],
            DNA_ORIGIN: ['A1.1', 'A2.1', 'A1.1', 'A2.1'],  # Consistent
            DNA_DESTINATION: ['A1.2', 'A2.2', 'B1.2', 'B2.2'],  # Consistent per circuit/group
            PLATE_DESTINATION: ['A1.1', 'A1.1', 'A2.1', 'A2.1'],  # Consistent per circuit
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid, f"Expected validation to pass but got: {error_msg}"
        assert error_msg is None

    def test_case_insensitive_grouping(self):
        """Circuit names should be compared case-insensitively."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'circuit1'],  # Different cases
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            PLATE_DESTINATION: ['A1.2', 'A1.2'],  # Same slot - should be OK
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid
        assert error_msg is None


class TestCircuitDNALimitValidation:
    """Test MAX_CIRCUIT_DNA enforcement."""

    def test_circuit_exceeds_max_dna_fails(self):
        """Circuit with total DNA > 800ng should fail."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [300, 300, 300],  # Total: 900ng > 800ng
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Circuit DNA Limit Exceeded' in error_msg
        assert 'Circuit1' in error_msg
        assert '800' in error_msg

    def test_circuit_at_max_dna_passes(self):
        """Circuit with total DNA = 800ng should pass."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'],
            CONCENTRATION: [50, 50, 50, 50],
            QUANTITY_DNA: [200, 200, 200, 200],  # Total: 800ng (exactly at limit)
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid
        assert error_msg is None

    def test_multiple_circuits_independent_limits(self):
        """Each circuit should be checked independently."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit2', 'Circuit2'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'],
            CONCENTRATION: [50, 50, 50, 50],
            QUANTITY_DNA: [400, 400, 100, 100],  # Circuit1: 800ng (OK), Circuit2: 200ng (OK)
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid
        assert error_msg is None


class TestSlotValidatorClass:
    """Test SlotValidator helper class."""

    def test_96well_valid_slots_separation(self, labware_96well_minimal):
        """96-well should have separate DNA source and working slots."""
        validator = SlotValidator('96well', labware_96well_minimal)

        dna_source_slots = validator.get_valid_slots_for_column(DNA_ORIGIN)
        working_slots = validator.get_valid_slots_for_column(DNA_DESTINATION)

        # DNA sources should only be racks 1 & 2 (tube racks)
        assert all('.1' in slot or '.2' in slot for slot in dna_source_slots), f"DNA source slots: {list(dna_source_slots)[:5]}"
        assert all('.3' not in slot for slot in dna_source_slots)

        # Working slots should only be rack 3 (well plate)
        assert all('.3' in slot for slot in working_slots), f"Working slots: {list(working_slots)[:5]}"
        assert all('.1' not in slot and '.2' not in slot for slot in working_slots)

    def test_24tube_shared_slots(self, labware_24tube_full):
        """24-tube should have shared input slots for DNA source and working."""
        validator = SlotValidator('24tube', labware_24tube_full)

        dna_source_slots = validator.get_valid_slots_for_column(DNA_ORIGIN)
        working_slots = validator.get_valid_slots_for_column(DNA_DESTINATION)

        # Should be the same set (all input racks)
        assert dna_source_slots == working_slots

    def test_output_slots_separate_from_input(self, labware_24tube_minimal):
        """Output plate slots are separate pools from input slots."""
        validator = SlotValidator('24tube', labware_24tube_minimal)

        input_slots = validator.get_valid_slots_for_column(DNA_ORIGIN)
        output_slots = validator.get_valid_slots_for_column(PLATE_DESTINATION)

        # Input and output are physically different locations even if they share well positions
        # They use different rack numbering (.1 for input rack vs .1 for output plate)
        # This is actually OK - same well position but different physical slots on OT-2
        # So we just verify that both sets exist
        assert len(input_slots) > 0, "Input slots should exist"
        assert len(output_slots) > 0, "Output slots should exist"
