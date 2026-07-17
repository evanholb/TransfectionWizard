"""
Assembly tab - DNA assembly interface.

This is a STARTING POINT, not the final version.
Goal tonight: get a working tab with basic fields and a table.
Real logic (connecting to PUDU, generating actual protocols) 
will be added with mentor guidance.
"""

# nicegui is the library that turns Python into a webpage.
# "ui" gives us building blocks like buttons, labels, inputs, tables.
from nicegui import ui

# These are our app's shared data containers (defined elsewhere in core/state.py)
from core.state import AppState, TemplateState


def create_assembly_tab(state: AppState, templates: TemplateState):
    """
    This function builds everything you see on the Assembly tab.
    It gets called once, when the page loads.

    Args:
        state: holds data shared across the whole app (like Design tab's table data)
        templates: holds template/config info (like the OT-2 Template dropdown)
    """

    # ui.column() stacks everything inside it vertically, top to bottom.
    # 'w-full' = take up full width. 'gap-4' = spacing between items.
    with ui.column().classes('w-full gap-4'):

        # --- TITLE ---
        ui.label('DNA Assembly').classes('text-xl font-bold')
        ui.label('Basic setup - fields and logic will expand with mentor input.').classes('text-gray-500')

        ui.separator()  # just a horizontal line, for visual separation

        # --- BASIC REACTION SETTINGS ---
        # These are simplified versions of PUDU's volume parameters.
        # ui.number() creates an input box that only accepts numbers.
        ui.label('Reaction Settings').classes('text-lg font-semibold')

        total_volume = ui.number('Total reaction volume (uL)', value=20)
        part_volume = ui.number('Part volume (uL)', value=2)
        replicates = ui.number('Replicates', value=1)

        ui.separator()

        # --- BASIC HARDWARE SETTINGS ---
        # ui.select() creates a dropdown menu with fixed choices.
        ui.label('Hardware').classes('text-lg font-semibold')

        pipette_choice = ui.select(
            ['p20_single_gen2', 'p300_single_gen2'],  # the dropdown options
            value='p20_single_gen2',                   # default selected option
            label='Pipette'
        )

        ui.separator()

        # --- TABLE FOR ASSEMBLY REACTIONS ---
        # This works like Design tab's table: each row = one experiment/reaction.
        ui.label('Assembly Reactions').classes('text-lg font-semibold')

        # Define what COLUMNS the table will have.
        # Each dictionary describes one column.
        columns = [
            {'name': 'circuit_name', 'label': 'Circuit name', 'field': 'circuit_name'},
            {'name': 'parts', 'label': 'Parts', 'field': 'parts'},
        ]

        # This list will hold the actual ROW data (starts empty).
        rows = []

        # Create the table using the columns/rows defined above.
        assembly_table = ui.table(columns=columns, rows=rows, row_key='circuit_name').classes('w-full')

        # This function runs every time "Add Row" is clicked.
        def add_row():
            # Add a new blank row to our rows list
            rows.append({
                'circuit_name': f'circuit_{len(rows) + 1}',  # auto-names it circuit_1, circuit_2, etc
                'parts': '',
            })
            # Tell the table to redraw itself with the new row included
            assembly_table.update()

        # Button that calls add_row() when clicked
        ui.button('Add Row', on_click=add_row)

        ui.separator()

        # --- PLACEHOLDER: NOT FUNCTIONAL YET ---
        # This button exists so the layout looks complete,
        # but it's disabled since there's no logic behind it yet.
        ui.label('Generate Protocol').classes('text-lg font-semibold')
        ui.button('Generate OT-2 Protocol').props('disable').tooltip(
            'Not connected yet - this is where PUDU logic will go'
        )