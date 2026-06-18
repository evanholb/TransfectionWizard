# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "Invalid: 96well Missing Required Slot 5 Test",
    "author": "Test",
    "description": "Tests invalid 96well layout missing required slot 5 (24-tube rack 2)"
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
    # load labware - INVALID: Has slot 6 but missing required slot 5
    tuberack1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="4"
    )

    wellplate2 = protocol.load_labware(
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
