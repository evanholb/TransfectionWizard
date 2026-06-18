# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "Invalid: No Output Plates Test",
    "author": "Test",
    "description": "Tests invalid layout with no output plates (missing required slot 2)"
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
    # load labware - INVALID: Only input racks, no output plates
    tuberack1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="4"
    )

    tuberack2 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="5"
    )

    tuberack3 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="6"
    )

    tiprack1 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", location="9"
    )

    tiprack2 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", location="8"
    )
