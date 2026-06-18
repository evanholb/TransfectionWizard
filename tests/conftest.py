"""Shared pytest fixtures for all tests."""

import pytest


@pytest.fixture
def labware_24tube_minimal():
    """Minimal 24-tube configuration: 1 input rack, 1 output plate."""
    return {
        '4': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '2': 'corning_24_wellplate_3.4ml_flat',
    }


@pytest.fixture
def labware_24tube_full():
    """Full 24-tube configuration: 3 input racks, 2 output plates."""
    return {
        '4': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '5': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '6': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '2': 'corning_24_wellplate_3.4ml_flat',
        '3': 'corning_24_wellplate_3.4ml_flat',
    }


@pytest.fixture
def labware_96well_minimal():
    """Minimal 96-well configuration: 2 tube racks, 1 well plate, 1 output plate."""
    return {
        '4': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '5': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '6': 'corning_96_wellplate_360ul_flat',
        '2': 'corning_24_wellplate_3.4ml_flat',
    }


@pytest.fixture
def labware_96well_full():
    """Full 96-well configuration: 2 tube racks, 1 well plate, 2 output plates."""
    return {
        '4': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '5': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '6': 'corning_96_wellplate_360ul_flat',
        '2': 'corning_24_wellplate_3.4ml_flat',
        '3': 'corning_24_wellplate_3.4ml_flat',
    }
