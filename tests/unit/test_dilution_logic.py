"""Tests for dilution detection logic."""

import pandas as pd
import pytest

from core.layout import detect_dilutions
from core.config import (
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA,
)


class TestDilutionDetection:
    """Test dilution detection based on minimum pipettable volume (2µL)."""

    def test_below_threshold_needs_dilution(self):
        """Dilution required when DNA_wanted < 2 * Concentration."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1', 'DNA2', 'DNA3'],
            CONCENTRATION: [100, 50, 10],  # ng/µL
            QUANTITY_DNA: [150, 200, 100]  # ng
        })

        needs_dilution = detect_dilutions(df)

        # DNA1: 150 < 2*100 (200) → True (volume would be 1.5µL, too small)
        # DNA2: 200 < 2*50 (100) → False (volume would be 4µL, OK)
        # DNA3: 100 < 2*10 (20) → False (volume would be 10µL, OK)
        assert needs_dilution.tolist() == [True, False, False]

    def test_at_threshold_no_dilution(self):
        """No dilution when exactly at threshold (2µL volume)."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1', 'DNA2'],
            CONCENTRATION: [100, 100],  # ng/µL
            QUANTITY_DNA: [200, 199]  # ng
        })

        needs_dilution = detect_dilutions(df)

        # DNA1: 200 < 2*100 → False (exactly 2µL, no dilution)
        # DNA2: 199 < 2*100 → True (1.99µL, needs dilution)
        assert needs_dilution.tolist() == [False, True]

    def test_above_threshold_no_dilution(self):
        """No dilution when well above threshold."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1', 'DNA2'],
            CONCENTRATION: [50, 25],
            QUANTITY_DNA: [500, 250],  # 10µL and 10µL respectively
        })

        needs_dilution = detect_dilutions(df)

        assert needs_dilution.tolist() == [False, False]

    def test_high_concentration_needs_dilution(self):
        """High concentration stock with low DNA wanted still needs dilution."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1'],
            CONCENTRATION: [500],  # Very concentrated
            QUANTITY_DNA: [100],   # Small amount wanted → 0.2µL
        })

        needs_dilution = detect_dilutions(df)

        # 100 < 2*500 (1000) → True (volume would be 0.2µL)
        assert needs_dilution.tolist() == [True]

    def test_missing_columns_no_dilution(self):
        """Missing columns should return False for all rows."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1', 'DNA2']
        })

        needs_dilution = detect_dilutions(df)
        assert needs_dilution.tolist() == [False, False]

    def test_nan_values_no_dilution(self):
        """NaN values in concentration or quantity should return False."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1', 'DNA2', 'DNA3'],
            CONCENTRATION: [None, 50, 50],
            QUANTITY_DNA: [100, None, 100],
        })

        needs_dilution = detect_dilutions(df)
        assert needs_dilution.tolist() == [False, False, False]

    def test_zero_concentration_no_dilution(self):
        """Zero concentration should return False (avoid division by zero)."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1'],
            CONCENTRATION: [0],
            QUANTITY_DNA: [100],
        })

        needs_dilution = detect_dilutions(df)
        assert needs_dilution.tolist() == [False]

    def test_zero_quantity_no_dilution(self):
        """Zero DNA wanted should return False."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1'],
            CONCENTRATION: [50],
            QUANTITY_DNA: [0],
        })

        needs_dilution = detect_dilutions(df)
        assert needs_dilution.tolist() == [False]

    def test_mixed_dilution_requirements(self):
        """Test dataset with mix of dilution needs."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['Part1', 'Part2', 'Part3', 'Part4', 'Part5'],
            CONCENTRATION: [100, 50, 200, 10, 75],
            QUANTITY_DNA: [50, 150, 100, 100, 149],
        })

        needs_dilution = detect_dilutions(df)

        # Part1: 50 < 200 → True (0.5µL)
        # Part2: 150 < 100 → False (3µL)
        # Part3: 100 < 400 → True (0.5µL)
        # Part4: 100 < 20 → False (10µL)
        # Part5: 149 < 150 → True (1.99µL)
        assert needs_dilution.tolist() == [True, False, True, False, True]

    def test_string_values_handled_gracefully(self):
        """Test that string values in numeric columns return False."""
        df = pd.DataFrame({
            DNA_PART_NAME: ['DNA1', 'DNA2'],
            CONCENTRATION: ['invalid', 50],
            QUANTITY_DNA: [100, 'invalid'],
        })

        needs_dilution = detect_dilutions(df)
        assert needs_dilution.tolist() == [False, False]
