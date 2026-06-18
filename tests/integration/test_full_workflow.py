"""Integration tests for complete validation and layout generation workflow."""

import pandas as pd
import pytest

from core.validation import validate_experiment_design
from core.layout import generate_layout, infer_circuits, infer_groups
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


class TestMinimalFormatWorkflow:
    """Test end-to-end workflow with minimal format input."""

    def test_simple_two_circuit_workflow(self):
        """Test complete workflow with simple two-circuit design."""
        # User provides minimal format
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit2', 'Circuit2'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'mKO2', 'Csy4'],
            CONCENTRATION: [50, 50, 50, 50],
            QUANTITY_DNA: [100, 100, 100, 100],
        })

        # Step 1: Validate
        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid, f"Validation failed: {error_msg}"

        # Step 2: Generate layout
        result = generate_layout(df, layout_key='24tube')

        # Verify all slots assigned
        assert (result[DNA_ORIGIN].notna() & (result[DNA_ORIGIN] != '')).all()
        assert (result[DNA_DESTINATION].notna() & (result[DNA_DESTINATION] != '')).all()
        assert (result[TRANSFECTION_DESTINATION].notna() & (result[TRANSFECTION_DESTINATION] != '')).all()
        assert (result[PLATE_DESTINATION].notna() & (result[PLATE_DESTINATION] != '')).all()

        # Verify grouping rules
        # mKO2 appears twice, should share DNA source
        mko2_rows = result[result[DNA_PART_NAME] == 'mKO2']
        assert len(mko2_rows[DNA_ORIGIN].unique()) == 1

        # Circuit1/X1 should share DNA and L3K destinations
        c1x1_rows = result[(result[CIRCUIT_NAME] == 'Circuit1') & (result[TRANSFECTION_GROUP] == 'X1')]
        assert len(c1x1_rows[DNA_DESTINATION].unique()) == 1
        assert len(c1x1_rows[TRANSFECTION_DESTINATION].unique()) == 1

        # Circuit1 should share plate destination
        c1_rows = result[result[CIRCUIT_NAME] == 'Circuit1']
        assert len(c1_rows[PLATE_DESTINATION].unique()) == 1

        # Circuit2 should have different plate destination
        c2_rows = result[result[CIRCUIT_NAME] == 'Circuit2']
        assert len(c2_rows[PLATE_DESTINATION].unique()) == 1
        assert c1_rows[PLATE_DESTINATION].iloc[0] != c2_rows[PLATE_DESTINATION].iloc[0]

    def test_workflow_with_dilutions(self):
        """Test workflow with DNA parts requiring dilution."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['HighConc', 'NormalConc', 'LowConc'],
            CONCENTRATION: [500, 50, 10],
            QUANTITY_DNA: [100, 100, 100],  # HighConc needs dilution (100 < 1000)
        })

        # Validate and generate
        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid

        result = generate_layout(df, layout_key='24tube')

        # HighConc should have diluted source
        highconc_row = result[result[DNA_PART_NAME] == 'HighConc'].iloc[0]
        assert pd.notna(highconc_row[DILUTED_SOURCE])
        assert highconc_row[DILUTED_SOURCE] != ''

        # NormalConc and LowConc should not have diluted sources
        normalconc_row = result[result[DNA_PART_NAME] == 'NormalConc'].iloc[0]
        lowconc_row = result[result[DNA_PART_NAME] == 'LowConc'].iloc[0]
        assert pd.isna(normalconc_row[DILUTED_SOURCE]) or normalconc_row[DILUTED_SOURCE] == ''
        assert pd.isna(lowconc_row[DILUTED_SOURCE]) or lowconc_row[DILUTED_SOURCE] == ''

    def test_workflow_with_multiple_groups(self):
        """Test workflow with multiple transfection groups per circuit."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X2', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'mKO2', 'Csy4'],
            CONCENTRATION: [50, 50, 50, 50],
            QUANTITY_DNA: [100, 100, 100, 100],
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid

        result = generate_layout(df, layout_key='24tube')

        # X1 and X2 should have different DNA destinations
        x1_dest = result[(result[CIRCUIT_NAME] == 'Circuit1') & (result[TRANSFECTION_GROUP] == 'X1')][DNA_DESTINATION].iloc[0]
        x2_dest = result[(result[CIRCUIT_NAME] == 'Circuit1') & (result[TRANSFECTION_GROUP] == 'X2')][DNA_DESTINATION].iloc[0]
        assert x1_dest != x2_dest

        # But all should share same plate destination (same circuit)
        assert len(result[PLATE_DESTINATION].unique()) == 1


class TestLegacyFormatWorkflow:
    """Test end-to-end workflow with legacy format (inferred circuits/groups)."""

    def test_legacy_format_inference_and_layout(self):
        """Test inference of circuits/groups from slot assignments, then layout generation."""
        # User provides slots, circuits/groups are blank
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'],
            CONCENTRATION: [50, 50, 50, 50],
            QUANTITY_DNA: [100, 100, 100, 100],
            DNA_DESTINATION: ['A1.1', 'A1.1', 'A2.1', 'A2.1'],
            PLATE_DESTINATION: ['A1.1', 'A1.1', 'A2.1', 'A2.1'],
            CIRCUIT_NAME: ['', '', '', ''],
            TRANSFECTION_GROUP: ['', '', '', ''],
        })

        # Step 1: Infer circuits from plate destinations
        df = infer_circuits(df)
        assert (df[CIRCUIT_NAME] != '').all()

        # Rows with same plate dest should get same circuit
        assert df.iloc[0][CIRCUIT_NAME] == df.iloc[1][CIRCUIT_NAME]
        assert df.iloc[2][CIRCUIT_NAME] == df.iloc[3][CIRCUIT_NAME]
        assert df.iloc[0][CIRCUIT_NAME] != df.iloc[2][CIRCUIT_NAME]

        # Step 2: Infer groups from DNA destinations
        df = infer_groups(df)
        assert (df[TRANSFECTION_GROUP] != '').all()

        # Rows with same DNA dest should get same group
        assert df.iloc[0][TRANSFECTION_GROUP] == df.iloc[1][TRANSFECTION_GROUP]
        assert df.iloc[2][TRANSFECTION_GROUP] == df.iloc[3][TRANSFECTION_GROUP]

        # Step 3: Validate
        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid

        # Step 4: Generate layout (fills missing slots)
        result = generate_layout(df, layout_key='24tube')

        # All slots should now be assigned
        assert (result[DNA_ORIGIN].notna() & (result[DNA_ORIGIN] != '')).all()
        assert (result[TRANSFECTION_DESTINATION].notna() & (result[TRANSFECTION_DESTINATION] != '')).all()

    def test_legacy_format_partial_slots(self):
        """Test legacy format where some slots are provided, others are blank."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [100, 100, 100],
            DNA_ORIGIN: ['A1.1', '', ''],  # Only first DNA source provided
            DNA_DESTINATION: ['B1.1', 'B1.1', 'A2.1'],  # First two share destination for grouping
            PLATE_DESTINATION: ['A1.1', 'A1.1', 'A2.1'],
            CIRCUIT_NAME: ['', '', ''],
            TRANSFECTION_GROUP: ['', '', ''],
        })

        # Infer circuits and groups
        df = infer_circuits(df)
        df = infer_groups(df)

        # Validate
        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid

        # Generate layout
        result = generate_layout(df, layout_key='24tube')

        # Manual assignments preserved
        assert result.iloc[0][DNA_ORIGIN] == 'A1.1'
        assert result.iloc[0][DNA_DESTINATION] == 'B1.1'
        assert result.iloc[1][DNA_DESTINATION] == 'B1.1'
        assert result.iloc[2][DNA_DESTINATION] == 'A2.1'

        # Missing DNA source assignments filled
        assert pd.notna(result.iloc[1][DNA_ORIGIN])
        assert pd.notna(result.iloc[2][DNA_ORIGIN])


class TestValidationBlocksInvalidLayouts:
    """Test that validation catches errors before layout generation."""

    def test_circuit_dna_limit_caught_before_layout(self):
        """Validation should catch circuit DNA limit violations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['Part1', 'Part2', 'Part3'],
            CONCENTRATION: [50, 50, 50],
            QUANTITY_DNA: [300, 300, 300],  # Total: 900ng > 800ng
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Circuit DNA Limit Exceeded' in error_msg
        assert '800' in error_msg

    def test_slot_conflict_caught_before_layout(self):
        """Validation should catch slot conflicts."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG'],  # Different parts
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.1', 'A1.1'],  # Same slot for different parts - CONFLICT
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Slot Conflict Errors' in error_msg

    def test_grouping_violation_caught_before_layout(self):
        """Validation should catch grouping rule violations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1'],
            TRANSFECTION_GROUP: ['X1', 'X2'],
            DNA_PART_NAME: ['mKO2', 'mKO2'],  # Same part
            CONCENTRATION: [50, 50],
            QUANTITY_DNA: [100, 100],
            DNA_ORIGIN: ['A1.1', 'A2.1'],  # Different sources - VIOLATION
        })

        is_valid, error_msg = validate_experiment_design(df)
        assert not is_valid
        assert 'Grouping Rule Violations' in error_msg


class TestComplexMultiCircuitWorkflow:
    """Test complex scenarios with multiple circuits, groups, and DNA parts."""

    def test_five_circuit_workflow(self):
        """Test workflow with 5 circuits, multiple groups, shared DNA parts."""
        df = pd.DataFrame({
            CIRCUIT_NAME: [
                'Circuit1', 'Circuit1', 'Circuit1', 'Circuit1',
                'Circuit2', 'Circuit2',
                'Circuit3', 'Circuit3', 'Circuit3',
                'Circuit4', 'Circuit4',
                'Circuit5', 'Circuit5', 'Circuit5', 'Circuit5'
            ],
            TRANSFECTION_GROUP: [
                'X1', 'X1', 'X2', 'X2',
                'X1', 'X1',
                'X1', 'X1', 'X1',
                'X1', 'X2',
                'X1', 'X1', 'X1', 'X1'
            ],
            DNA_PART_NAME: [
                'mKO2', 'mNG', 'mKO2', 'Csy4',  # mKO2 shared between groups
                'PacBlue', 'YFP',
                'mKO2', 'mNG', 'GFP',  # mKO2 and mNG shared with Circuit1
                'RFP', 'CFP',
                'mKO2', 'mNG', 'Csy4', 'PacBlue'  # All shared with other circuits
            ],
            CONCENTRATION: [50] * 15,
            QUANTITY_DNA: [100] * 15,
        })

        # Validate
        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid, f"Validation failed: {error_msg}"

        # Generate layout
        result = generate_layout(df, layout_key='24tube')

        # Verify shared DNA parts have same source
        mko2_sources = result[result[DNA_PART_NAME] == 'mKO2'][DNA_ORIGIN].unique()
        assert len(mko2_sources) == 1

        mng_sources = result[result[DNA_PART_NAME] == 'mNG'][DNA_ORIGIN].unique()
        assert len(mng_sources) == 1

        # Verify each circuit gets unique plate destination
        plate_dests = result.groupby(CIRCUIT_NAME)[PLATE_DESTINATION].apply(lambda x: x.iloc[0])
        assert len(plate_dests.unique()) == 5

        # Verify each circuit/group combo gets unique DNA destination
        dna_dests = result.groupby([CIRCUIT_NAME, TRANSFECTION_GROUP])[DNA_DESTINATION].apply(lambda x: x.iloc[0])
        assert len(dna_dests.unique()) == len(dna_dests)

    def test_workflow_with_all_features(self):
        """Test workflow with circuits, multiple groups, dilutions, and manual assignments."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1', 'Circuit2', 'Circuit2'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X2', 'X1', 'X1'],
            DNA_PART_NAME: ['HighConc', 'NormalConc', 'HighConc', 'LowConc', 'NormalConc'],
            CONCENTRATION: [500, 50, 500, 10, 50],
            QUANTITY_DNA: [100, 100, 100, 100, 100],
            DNA_ORIGIN: ['A1.1', '', '', '', ''],  # Manual assignment for HighConc
            PLATE_DESTINATION: ['', '', '', 'A2.1', 'A2.1'],  # Manual assignment for Circuit2
        })

        # Validate
        is_valid, error_msg = validate_experiment_design(df)
        assert is_valid

        # Generate layout
        result = generate_layout(df, layout_key='24tube')

        # Manual assignments preserved
        highconc_row = result[(result[DNA_PART_NAME] == 'HighConc') & (result[CIRCUIT_NAME] == 'Circuit1')].iloc[0]
        assert highconc_row[DNA_ORIGIN] == 'A1.1'

        circuit2_plate = result[result[CIRCUIT_NAME] == 'Circuit2'][PLATE_DESTINATION].iloc[0]
        assert circuit2_plate == 'A2.1'

        # Dilutions assigned for HighConc parts
        highconc_rows = result[result[DNA_PART_NAME] == 'HighConc']
        assert (highconc_rows[DILUTED_SOURCE].notna() & (highconc_rows[DILUTED_SOURCE] != '')).all()

        # HighConc parts share diluted source (same DNA part)
        assert len(highconc_rows[DILUTED_SOURCE].unique()) == 1

        # NormalConc shared between circuits
        normalconc_sources = result[result[DNA_PART_NAME] == 'NormalConc'][DNA_ORIGIN].unique()
        assert len(normalconc_sources) == 1
