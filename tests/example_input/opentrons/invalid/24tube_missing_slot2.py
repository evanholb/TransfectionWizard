# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "Invalid: 24tube Missing Required Slot 2 Test",
    "author": "Test",
    "description": "Tests invalid 24tube layout missing required slot 2 (output plate 1)"
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
    # load labware - INVALID: Has slot 3 but missing required slot 2
    tuberack1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="4"
    )

    tuberack2 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="5"
    )

    tuberack3 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="6"
    )

    plate2 = protocol.load_labware(
        "corning_24_wellplate_3.4ml_flat", location="3"
    )

    tiprack1 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", location="9"
    )

    tiprack2 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", location="8"
    )
