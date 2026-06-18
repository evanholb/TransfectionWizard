"""Tests for Circuit name and Transfection group inference logic."""

import pandas as pd
import pytest

from core.layout import infer_circuits, infer_groups
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
)


class TestCircuitInference:
    """Test Circuit name inference from Plate destinations."""

    def test_infer_circuits_from_plate_destinations(self):
        """Circuits should be inferred from unique Plate destinations."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'],
            CONCENTRATION: [50, 50, 25, 100],
            QUANTITY_DNA: [100, 100, 50, 150],
            PLATE_DESTINATION: ['A1.1', 'A1.1', 'A2.1', 'A2.1'],
            CIRCUIT_NAME: ['', '', '', ''],  # All blank
        })

        result = infer_circuits(df)

        # Rows with same Plate dest should get same Circuit
        assert result.iloc[0][CIRCUIT_NAME] == result.iloc[1][CIRCUIT_NAME]
        assert result.iloc[2][CIRCUIT_NAME] == result.iloc[3][CIRCUIT_NAME]

        # Rows with different Plate dest should get different Circuits
        assert result.iloc[0][CIRCUIT_NAME] != result.iloc[2][CIRCUIT_NAME]

        # Should be numbered Circuit1, Circuit2
        circuits = set(result[CIRCUIT_NAME].values)
        assert 'Circuit1' in circuits
        assert 'Circuit2' in circuits

    def test_infer_circuits_preserves_existing(self):
        """If some rows have Circuit names, preserve them for matching Plate destinations."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            PLATE_DESTINATION: ['A1.1', 'A1.1', 'A2.1'],
            CIRCUIT_NAME: ['MyCircuit', '', ''],  # First row has custom name
        })

        result = infer_circuits(df)

        # All rows with Plate dest A1.1 should use "MyCircuit"
        assert result.iloc[0][CIRCUIT_NAME] == 'MyCircuit'
        assert result.iloc[1][CIRCUIT_NAME] == 'MyCircuit'

        # Row with different Plate dest gets new Circuit
        assert result.iloc[2][CIRCUIT_NAME] != 'MyCircuit'
        assert result.iloc[2][CIRCUIT_NAME].startswith('Circuit')

    def test_infer_circuits_handles_no_plate_destinations(self):
        """When no Plate destinations exist, don't crash."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2'],
            CIRCUIT_NAME: [''],
            PLATE_DESTINATION: [''],  # Blank
        })

        result = infer_circuits(df)

        # Should remain blank if no Plate destination to infer from
        assert result.iloc[0][CIRCUIT_NAME] == ''

    def test_infer_circuits_numbering_avoids_conflicts(self):
        """Circuit numbering should skip existing Circuit names."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            PLATE_DESTINATION: ['A1.1', 'A2.1', 'A3.1'],
            CIRCUIT_NAME: ['Circuit1', '', ''],  # Circuit1 already used
        })

        result = infer_circuits(df)

        # Should skip Circuit1 and use Circuit2, Circuit3
        circuits = set(result[CIRCUIT_NAME].values)
        assert 'Circuit1' in circuits  # Preserved
        assert 'Circuit2' in circuits  # Auto-assigned
        assert 'Circuit3' in circuits  # Auto-assigned


class TestGroupInference:
    """Test Transfection group inference from DNA destinations."""

    def test_infer_groups_from_dna_destinations(self):
        """Groups should be inferred from unique DNA destinations within each circuit."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1', 'Circuit1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'],
            DNA_DESTINATION: ['A1.2', 'A1.2', 'A2.2', 'A2.2'],
            TRANSFECTION_GROUP: ['', '', '', ''],  # All blank
        })

        result = infer_groups(df)

        # Rows with same DNA dest should get same Group
        assert result.iloc[0][TRANSFECTION_GROUP] == result.iloc[1][TRANSFECTION_GROUP]
        assert result.iloc[2][TRANSFECTION_GROUP] == result.iloc[3][TRANSFECTION_GROUP]

        # Rows with different DNA dest should get different Groups
        assert result.iloc[0][TRANSFECTION_GROUP] != result.iloc[2][TRANSFECTION_GROUP]

        # Should be numbered X1, X2
        groups = set(result[TRANSFECTION_GROUP].values)
        assert 'X1' in groups
        assert 'X2' in groups

    def test_infer_groups_per_circuit(self):
        """Groups should be numbered independently for each circuit."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit2', 'Circuit2'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4', 'PacBlue'],
            DNA_DESTINATION: ['A1.2', 'A2.2', 'A1.2', 'A2.2'],  # Same slots, different circuits
            TRANSFECTION_GROUP: ['', '', '', ''],
        })

        result = infer_groups(df)

        # Circuit1 should have X1, X2
        circuit1_groups = result[result[CIRCUIT_NAME] == 'Circuit1'][TRANSFECTION_GROUP].values
        assert set(circuit1_groups) == {'X1', 'X2'}

        # Circuit2 should also have X1, X2 (independent numbering)
        circuit2_groups = result[result[CIRCUIT_NAME] == 'Circuit2'][TRANSFECTION_GROUP].values
        assert set(circuit2_groups) == {'X1', 'X2'}

    def test_infer_groups_preserves_existing(self):
        """If some rows have Group names, preserve them for matching DNA destinations."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            DNA_DESTINATION: ['A1.2', 'A1.2', 'A2.2'],
            TRANSFECTION_GROUP: ['Control', '', ''],  # First row has custom name
        })

        result = infer_groups(df)

        # All rows with DNA dest A1.2 should use "Control"
        assert result.iloc[0][TRANSFECTION_GROUP] == 'Control'
        assert result.iloc[1][TRANSFECTION_GROUP] == 'Control'

        # Row with different DNA dest gets new Group
        assert result.iloc[2][TRANSFECTION_GROUP] != 'Control'
        assert result.iloc[2][TRANSFECTION_GROUP].startswith('X')

    def test_infer_groups_case_insensitive_circuits(self):
        """Circuit names should be compared case-insensitively."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'circuit1', 'CIRCUIT1'],  # Different cases
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            DNA_DESTINATION: ['A1.2', 'A2.2', 'A3.2'],
            TRANSFECTION_GROUP: ['', '', ''],
        })

        result = infer_groups(df)

        # All should be treated as same circuit, get X1, X2, X3
        groups = result[TRANSFECTION_GROUP].values
        assert len(set(groups)) == 3  # Three unique groups
        assert all(g.startswith('X') for g in groups)


class TestInferenceWorkflow:
    """Test inference in realistic workflows."""

    def test_legacy_format_full_inference(self):
        """Legacy format: both circuits and groups get inferred."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 25],
            QUANTITY_DNA: [100, 100, 50],
            DNA_ORIGIN: ['A1.1', 'A2.1', 'A3.1'],
            DNA_DESTINATION: ['A1.2', 'A1.2', 'A2.2'],
            TRANSFECTION_DESTINATION: ['A1.3', 'A1.3', 'A2.3'],
            PLATE_DESTINATION: ['A1.1', 'A1.1', 'A2.1'],
            CIRCUIT_NAME: ['', '', ''],
            TRANSFECTION_GROUP: ['', '', ''],
        })

        # Step 1: Infer circuits
        df = infer_circuits(df)
        assert (df[CIRCUIT_NAME] != '').all()

        # Step 2: Infer groups
        df = infer_groups(df)
        assert (df[TRANSFECTION_GROUP] != '').all()

        # Verify grouping correctness
        # Rows 0-1: same Plate dest → same Circuit, same DNA dest → same Group
        assert df.iloc[0][CIRCUIT_NAME] == df.iloc[1][CIRCUIT_NAME]
        assert df.iloc[0][TRANSFECTION_GROUP] == df.iloc[1][TRANSFECTION_GROUP]

        # Row 2: different Plate dest → different Circuit
        assert df.iloc[0][CIRCUIT_NAME] != df.iloc[2][CIRCUIT_NAME]

    def test_minimal_format_no_inference_needed(self):
        """Minimal format: circuits and groups already provided, no inference."""
        df = pd.DataFrame({
            CIRCUIT_NAME: ['Circuit1', 'Circuit1', 'Circuit2'],
            TRANSFECTION_GROUP: ['X1', 'X1', 'X1'],
            DNA_PART_NAME: ['mKO2', 'mNG', 'Csy4'],
            CONCENTRATION: [50, 50, 25],
            QUANTITY_DNA: [100, 100, 50],
            PLATE_DESTINATION: ['', '', ''],  # Will be assigned during layout
        })

        # Inference should not change anything
        original_circuits = df[CIRCUIT_NAME].copy()
        original_groups = df[TRANSFECTION_GROUP].copy()

        df = infer_circuits(df)
        df = infer_groups(df)

        # Should be unchanged
        assert df[CIRCUIT_NAME].equals(original_circuits)
        assert df[TRANSFECTION_GROUP].equals(original_groups)
