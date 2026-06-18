# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "Minimal 96well Layout Test",
    "author": "Test",
    "description": "Tests minimal 96well layout with only required slots 2, 4, 5"
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

# csv import
csv_raw = '''DNA source,DNA destination,L3K/OM MM destination,Plate destination,Transfection type,Contents,Concentration (ng/uL),DNA wanted (ng)
'''

csv_data = csv_raw.splitlines()
csv_reader = csv.DictReader(csv_data)

# protocol run function
def run(protocol: protocol_api.ProtocolContext):
    # load labware - MINIMAL 96WELL: slots 2 (output), 4 (tube rack 1), 5 (tube rack 2), 6 (96-well plate)
    tuberack1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="4"
    )

    tuberack2 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="5"
    )

    wellplate1 = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", location="6"
    )

    plate1 = protocol.load_labware(
        "corning_24_wellplate_3.4ml_flat", location="2"
    )

    tiprack1 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", location="9"
    )

    tiprack2 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", location="8"
    )
