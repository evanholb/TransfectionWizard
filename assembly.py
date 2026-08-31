"""
Assembly tab - DNA assembly interface.
"""

from nicegui import ui
import csv
import io
import asyncio
import json as json_module
import zipfile
from io import BytesIO

from core.state import AppState, TemplateState
from ui.components.simulation import run_opentrons_simulation


def generate_well_order(num_rows: int, num_cols: int) -> list:
    row_letters = [chr(ord('A') + i) for i in range(num_rows)]
    wells = []
    for col in range(1, num_cols + 1):
        for row in row_letters:
            wells.append(f'{row}{col}')
    return wells


REAGENT_WELLS = generate_well_order(4, 6)
PARTS_WELLS = generate_well_order(4, 6)
REACTION_WELLS = generate_well_order(8, 12)

# Last 3 wells of the reagent plate (D5, A6, B6 in well order) are always
# ligase/buffer/water. Every other well on the plate is fair game for enzymes,
# so up to 21 unique enzymes can be tracked (was capped at 4).
LIGASE_WELL = REAGENT_WELLS[-3]
BUFFER_WELL = REAGENT_WELLS[-2]
WATER_WELL = REAGENT_WELLS[-1]
ENZYME_WELLS_POOL = REAGENT_WELLS[:-3]


def create_assembly_tab(state: AppState, templates: TemplateState):
    with ui.column().classes('w-full gap-4'):

        ui.label('DNA Assembly').classes('text-xl font-bold')
        ui.label('DNA assembly setup for OT-2 protocol generation.').classes('text-gray-500')
        ui.separator()

        ui.label('Step 1: Reaction Settings').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Total reaction volume is how much liquid ends up in each '
                'reaction well overall. Part volume is how much of EACH '
                'individual DNA part goes in.'
            ).classes('text-gray-500 text-sm')
        total_volume = ui.number('Total reaction volume (uL)', value=20).style('width: 300px')
        part_volume = ui.number('Part volume (uL)', value=2).style('width: 300px')
        volume_sum_warning = ui.label('').classes('text-orange-600 text-sm')
        ui.separator()

        ui.label('Step 2: Hardware').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Pipette is which liquid-handling tool the robot uses. Tip '
                'racks, the parts rack, and the temp module all share slots '
                '1-6 - they can go in any of those slots. The temp module '
                'keeps reagents cold during setup, then turns off once '
                'reactions are loaded - it has no more work to do once the '
                'thermocycler takes over.'
            ).classes('text-gray-500 text-sm')

        with ui.column().classes('gap-0'):
            ui.label('Pipette').classes('font-bold text-sm')
            pipette_choice = ui.select(['p20_single_gen2', 'p300_single_gen2'], value='p20_single_gen2').classes('w-full')

        with ui.grid(columns=3).classes('w-full gap-4'):
            with ui.column().classes('gap-0'):
                ui.label('Tip Rack 1 Deck Slot').classes('font-bold text-sm')
                tiprack_slot_1 = ui.select(['1', '2', '3', '4', '5', '6'], value='1').classes('w-full')
            with ui.column().classes('gap-0'):
                ui.label('Tip Rack 2 Deck Slot').classes('font-bold text-sm')
                tiprack_slot_2 = ui.select(['1', '2', '3', '4', '5', '6'], value='2').classes('w-full')
            with ui.column().classes('gap-0'):
                ui.label('Tip Rack 3 Deck Slot').classes('font-bold text-sm')
                tiprack_slot_3 = ui.select(['1', '2', '3', '4', '5', '6'], value='3').classes('w-full')

        pipette_warning = ui.label('').classes('text-red-500 text-sm')
        ui.separator()

        ui.label('Step 3: Cloning Protocol').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'For each reaction, in order: 1) DNA parts, 2) T4 ligase and '
                'buffer, 3) water to top off the volume, 4) enzyme added last, '
                'then everything is mixed at 75% of the total reaction volume. '
                'Enzyme choice can be set per reaction in the CSV (Step 4).'
            ).classes('text-gray-500 text-sm')

        with ui.grid(columns=4).classes('w-full gap-4'):
            enzyme_volume = ui.number('Enzyme volume (uL)', value=2)
            ligase_volume = ui.number('T4 DNA ligase volume (uL)', value=4)
            buffer_volume = ui.number('T4 ligase buffer volume (uL)', value=2)
            with ui.column().classes('gap-0'):
                ui.label('Temperature Module Deck Slot').classes('font-bold text-sm')
                temp_module_slot = ui.select(['1', '2', '3', '4', '5', '6'], value='4').classes('w-full')

        with ui.column().classes('gap-0'):
            ui.label('DNA Parts Rack Deck Slot').classes('font-bold text-sm')
            parts_rack_slot = ui.select(['1', '2', '3', '4', '5', '6'], value='6').classes('w-full')

        def check_pipette_range():
            max_vol = max(enzyme_volume.value, ligase_volume.value, buffer_volume.value, part_volume.value)
            if pipette_choice.value == 'p20_single_gen2' and max_vol > 20:
                pipette_warning.text = f'Warning: p20 only goes up to 20uL, but you entered {max_vol}. Switch to p300.'
            elif pipette_choice.value == 'p300_single_gen2' and max_vol < 20:
                pipette_warning.text = 'Note: p300 works best above 20uL.'
            else:
                pipette_warning.text = ''

        def check_volume_sum():
            combined = enzyme_volume.value + ligase_volume.value + buffer_volume.value + part_volume.value
            if combined > total_volume.value:
                volume_sum_warning.text = (
                    f'Warning: enzyme + ligase + buffer + one part volume already add up to '
                    f'{combined}uL, more than your total of {total_volume.value}uL.'
                )
            else:
                volume_sum_warning.text = ''

        def on_any_volume_change():
            check_pipette_range()
            check_volume_sum()
            create_layout()

        pipette_choice.on_value_change(lambda: on_any_volume_change())
        enzyme_volume.on_value_change(lambda: on_any_volume_change())
        ligase_volume.on_value_change(lambda: on_any_volume_change())
        buffer_volume.on_value_change(lambda: on_any_volume_change())
        part_volume.on_value_change(lambda: on_any_volume_change())
        total_volume.on_value_change(lambda: on_any_volume_change())
        ui.separator()

        ui.label('Step 4: Assembly Reactions').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Upload a CSV and it shows up here as an editable spreadsheet. '
                'Supports two formats: wide (one row per circuit, parts '
                'comma-separated) or long (one row per individual part, '
                'circuit_name repeats). An optional "enzyme" column sets which '
                'enzyme a reaction uses (defaults to BsaI if left blank).'
            ).classes('text-gray-500 text-sm')

        ui.label(
            'Wide format: circuit_name,parts,enzyme (e.g. "circuit_1,partA,partB,backbone1,BsmBI"). '
            'Long format: circuit_name,part,enzyme (one part per row, circuit_name repeats).'
        ).classes('text-gray-400 text-xs italic')

        rows = []
        column_headers = []
        grid_container = ui.column().classes('w-full')
        assembly_grid = {'ref': None}

        def humanize_header(header: str) -> str:
            if header.strip().lower() == 'parts':
                return 'DNA Parts (comma-separated)'
            if header.strip().lower() == 'enzyme':
                return 'Enzyme (optional, defaults to BsaI)'
            return header.replace('_', ' ').title()

        def reassign_wells():
            for i, row in enumerate(rows):
                row['_reaction_well'] = REACTION_WELLS[i] if i < len(REACTION_WELLS) else 'OUT OF WELLS'
            update_generate_button_state()
            sync_parts_from_rows()
            sync_enzymes_from_rows()
            render_enzyme_list()
            create_layout()

        def render_grid():
            grid_container.clear()
            with grid_container:
                if not rows or not column_headers:
                    ui.label('No data yet - upload a CSV or add a row below.').classes('text-gray-400 text-sm italic')
                    return

                column_defs = [
                    {'field': h, 'headerName': humanize_header(h), 'editable': True}
                    for h in column_headers
                ]
                grid = ui.aggrid({
                    'columnDefs': column_defs,
                    'rowData': rows,
                    'rowSelection': 'multiple',
                    'stopEditingWhenCellsLoseFocus': True,
                    'defaultColDef': {'editable': True, 'sortable': True, 'filter': True},
                }).classes('w-full').style('height: 300px')
                assembly_grid['ref'] = grid

                async def on_cell_changed(e):
                    client_rows = await grid.get_client_data()
                    rows.clear()
                    rows.extend(client_rows)
                    reassign_wells()

                grid.on('cellValueChanged', on_cell_changed)

                with ui.row().classes('gap-2 mt-2'):
                    async def handle_delete_selected():
                        selected = await grid.get_selected_rows()
                        if not selected:
                            ui.notify('No rows selected', type='warning')
                            return
                        for sel_row in selected:
                            if sel_row in rows:
                                rows.remove(sel_row)
                        reassign_wells()
                        render_grid()
                        ui.notify(f'Deleted {len(selected)} row(s)')

                    ui.button('Delete Selected', icon='delete', on_click=handle_delete_selected).props('flat color=negative')

        async def handle_csv_upload(e):
            """
            Handles both CSV formats:
            - WIDE: one row per circuit, parts already comma-separated
            - LONG: one row per individual part, circuit_name repeats
            Long format gets converted into wide format internally.
            """
            text = await e.file.text()
            reader = csv.DictReader(io.StringIO(text))
            raw_rows = list(reader)
            fieldnames = reader.fieldnames or []

            has_singular_part = any(h.strip().lower() == 'part' for h in fieldnames)
            has_plural_parts = any(h.strip().lower() == 'parts' for h in fieldnames)

            if has_singular_part and not has_plural_parts:
                circuit_col = fieldnames[0]
                part_col = next(h for h in fieldnames if h.strip().lower() == 'part')
                enzyme_col = next((h for h in fieldnames if h.strip().lower() == 'enzyme'), None)

                grouped = {}
                order = []
                for r in raw_rows:
                    key = r.get(circuit_col, '').strip()
                    if key not in grouped:
                        grouped[key] = {'parts_list': [], 'enzyme': ''}
                        order.append(key)
                    part_val = r.get(part_col, '').strip()
                    if part_val:
                        grouped[key]['parts_list'].append(part_val)
                    if enzyme_col:
                        enzyme_val = r.get(enzyme_col, '').strip()
                        if enzyme_val and not grouped[key]['enzyme']:
                            grouped[key]['enzyme'] = enzyme_val

                rows.clear()
                column_headers.clear()
                column_headers.append(circuit_col)
                column_headers.append('parts')
                if enzyme_col:
                    column_headers.append('enzyme')

                for key in order:
                    new_row = {circuit_col: key, 'parts': ','.join(grouped[key]['parts_list'])}
                    if enzyme_col:
                        new_row['enzyme'] = grouped[key]['enzyme']
                    rows.append(new_row)

                ui.notify(f'Converted long-format CSV: {len(rows)} circuit(s) from {len(raw_rows)} rows')
            else:
                rows.clear()
                column_headers.clear()
                rows.extend(raw_rows)
                column_headers.extend(fieldnames)
                ui.notify(f'Loaded {len(rows)} row(s)')

            reassign_wells()
            render_grid()

        ui.upload(label='Upload Assembly CSV File', on_upload=handle_csv_upload, auto_upload=True).props('accept=.csv')

        def add_row():
            if not column_headers:
                ui.notify('Upload a CSV first to set up columns', type='warning')
                return
            rows.append({header: '' for header in column_headers})
            reassign_wells()
            render_grid()

        ui.button('Add Row', on_click=add_row)
        render_grid()
        ui.separator()

        def find_parts_column():
            for header in column_headers:
                if header.strip().lower() == 'parts':
                    return header
            return None

        def find_enzyme_column():
            for header in column_headers:
                if header.strip().lower() == 'enzyme':
                    return header
            return None

        def get_part_to_well_map():
            return {p['name']: PARTS_WELLS[i] for i, p in enumerate(parts_registry) if i < len(PARTS_WELLS)}

        def get_row_enzyme_name(row: dict) -> str:
            enzyme_col = find_enzyme_column()
            if enzyme_col:
                raw = row.get(enzyme_col, '').strip()
                if raw:
                    return raw
            return 'BsaI'

        enzyme_registry = []

        def sync_enzymes_from_rows():
            """Auto-adds any enzyme named in the CSV's enzyme column to the registry,
            in order of first appearance. Manually-added enzymes (add_manual_enzyme)
            are kept even if no row currently uses them."""
            existing_names = [e['name'] for e in enzyme_registry]
            for row in rows:
                name = get_row_enzyme_name(row)
                if name not in existing_names:
                    enzyme_registry.append({'name': name})
                    existing_names.append(name)

        def get_unique_enzymes() -> list:
            """Returns tracked enzyme names, in order of first appearance/addition."""
            return [e['name'] for e in enzyme_registry]

        def get_enzyme_to_well_map():
            """Each tracked enzyme gets its own well - no two enzymes share a tube."""
            unique_enzymes = get_unique_enzymes()
            return {name: ENZYME_WELLS_POOL[i] for i, name in enumerate(unique_enzymes) if i < len(ENZYME_WELLS_POOL)}

        def get_reaction_detail(row: dict) -> dict:
            """
            Single source of truth for what goes into one reaction well.
            Order: parts -> ligase + buffer -> water -> enzyme (added last).
            Used by Deck Layout popup AND protocol generation.
            """
            parts_col = find_parts_column()
            enzyme_name = get_row_enzyme_name(row)
            enzyme_to_well = get_enzyme_to_well_map()
            enzyme_well = enzyme_to_well.get(enzyme_name, 'NO WELL ASSIGNED')

            row_parts_names = []
            if parts_col:
                raw = row.get(parts_col, '')
                row_parts_names = [p.strip() for p in str(raw).split(',') if p.strip()]

            part_to_well = get_part_to_well_map()
            parts_detail = [
                {'name': name, 'well': part_to_well.get(name, 'NO WELL ASSIGNED'), 'volume_uL': part_volume.value}
                for name in row_parts_names
            ]

            # Order: ligase + buffer first, then water, then enzyme LAST
            reagents_detail = [
                {'name': 'T4 Ligase', 'well': LIGASE_WELL, 'volume_uL': ligase_volume.value},
                {'name': 'Buffer', 'well': BUFFER_WELL, 'volume_uL': buffer_volume.value},
            ]

            used_volume = (
                enzyme_volume.value + ligase_volume.value + buffer_volume.value
                + (part_volume.value * len(row_parts_names))
            )
            water_volume = max(0, total_volume.value - used_volume)
            if water_volume > 0:
                reagents_detail.append({'name': 'Water', 'well': WATER_WELL, 'volume_uL': water_volume})

            # Enzyme added LAST, right before mixing
            reagents_detail.append({'name': enzyme_name, 'well': enzyme_well, 'volume_uL': enzyme_volume.value})

            label_col = column_headers[0] if column_headers else None
            circuit_name = row.get(label_col, row.get('_reaction_well', '')) if label_col else row.get('_reaction_well', '')

            return {
                'circuit_name': circuit_name,
                'well': row.get('_reaction_well', ''),
                'enzyme': enzyme_name,
                'parts': parts_detail,
                'reagents': reagents_detail,
            }

        ui.label('Step 5: DNA Parts').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Real list of DNA parts pulled from physical tubes. Auto-fills '
                'from your CSV\'s "parts" column, or add one manually. Each '
                'part gets one well on the parts rack (slot set above).'
            ).classes('text-gray-500 text-sm')

        parts_registry = []
        parts_list_container = ui.column().classes('w-full gap-1')
        new_part_name_input = {'ref': None}

        def sync_parts_from_rows():
            parts_col = find_parts_column()
            if not parts_col:
                return
            existing_names = [p['name'] for p in parts_registry]
            for row in rows:
                raw = row.get(parts_col, '')
                for part in str(raw).split(','):
                    part = part.strip()
                    if part and part not in existing_names:
                        parts_registry.append({'name': part})
                        existing_names.append(part)
            render_parts_list()

        def render_parts_list():
            parts_list_container.clear()
            with parts_list_container:
                if not parts_registry:
                    ui.label('No parts tracked yet - upload a CSV or add one manually below.').classes('text-gray-400 text-sm italic')
                    return

                with ui.row().classes('w-full gap-2 font-bold text-sm'):
                    ui.label('Part Name').classes('w-48')
                    ui.label('Assigned Well').classes('w-32')
                    ui.label('').classes('w-10')

                for i, part in enumerate(parts_registry):
                    with ui.row().classes('w-full gap-2 items-center'):
                        def make_name_handler(p=part):
                            def handler(e):
                                p['name'] = e.value
                            return handler

                        def make_delete_handler(p=part):
                            def handler():
                                parts_registry.remove(p)
                                render_parts_list()
                                create_layout()
                            return handler

                        ui.input(value=part['name'], on_change=make_name_handler()).classes('w-48')
                        assigned_well = PARTS_WELLS[i] if i < len(PARTS_WELLS) else 'NO WELL'
                        ui.label(assigned_well).classes('w-32 font-mono text-gray-500')
                        ui.button(icon='delete', on_click=make_delete_handler()).props('flat dense').classes('w-10')

        def add_manual_part():
            name = new_part_name_input['ref'].value.strip()
            if not name:
                ui.notify('Enter a part name first', type='warning')
                return
            if any(p['name'] == name for p in parts_registry):
                ui.notify('That part is already tracked', type='warning')
                return
            parts_registry.append({'name': name})
            new_part_name_input['ref'].value = ''
            render_parts_list()
            create_layout()

        render_parts_list()

        with ui.row().classes('gap-2 items-end mt-2'):
            with ui.column().classes('gap-0'):
                ui.label('New Part Name').classes('text-xs text-gray-600')
                new_part_name_input['ref'] = ui.input(placeholder='e.g. mKO2').classes('w-48')
            ui.button('Add Part', icon='add', on_click=add_manual_part)

        if len(parts_registry) > len(PARTS_WELLS):
            ui.label(f'Warning: more parts tracked than the rack has wells ({len(PARTS_WELLS)} max).').classes('text-orange-600 text-sm mt-2')

        ui.separator()

        ui.label('Step 5b: Enzyme Registry').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Every unique enzyme used across your reactions (from the CSV '
                '"enzyme" column, defaulting to BsaI) gets tracked here with its '
                'own well - no two enzymes ever share a tube. Add a custom enzyme '
                'manually below even before it shows up in a reaction, or just '
                'set different enzymes per row in Step 4 to run multiple circuits '
                'with different parts/enzymes side by side.'
            ).classes('text-gray-500 text-sm')

        enzyme_list_container = ui.column().classes('w-full gap-1')
        new_enzyme_name_input = {'ref': None}

        def render_enzyme_list():
            enzyme_list_container.clear()
            with enzyme_list_container:
                if not enzyme_registry:
                    ui.label('No enzymes tracked yet - upload a CSV with an "enzyme" column or add one manually below.').classes('text-gray-400 text-sm italic')
                    return

                with ui.row().classes('w-full gap-2 font-bold text-sm'):
                    ui.label('Enzyme Name').classes('w-48')
                    ui.label('Assigned Well').classes('w-32')
                    ui.label('').classes('w-10')

                for i, enzyme in enumerate(enzyme_registry):
                    with ui.row().classes('w-full gap-2 items-center'):
                        def make_name_handler(e=enzyme):
                            def handler(ev):
                                e['name'] = ev.value
                            return handler

                        def make_delete_handler(e=enzyme):
                            def handler():
                                enzyme_registry.remove(e)
                                render_enzyme_list()
                                create_layout()
                            return handler

                        ui.input(value=enzyme['name'], on_change=make_name_handler()).classes('w-48')
                        assigned_well = ENZYME_WELLS_POOL[i] if i < len(ENZYME_WELLS_POOL) else 'NO WELL'
                        ui.label(assigned_well).classes('w-32 font-mono text-gray-500')
                        ui.button(icon='delete', on_click=make_delete_handler()).props('flat dense').classes('w-10')

        def add_manual_enzyme():
            name = new_enzyme_name_input['ref'].value.strip()
            if not name:
                ui.notify('Enter an enzyme name first', type='warning')
                return
            if any(e['name'] == name for e in enzyme_registry):
                ui.notify('That enzyme is already tracked', type='warning')
                return
            enzyme_registry.append({'name': name})
            new_enzyme_name_input['ref'].value = ''
            render_enzyme_list()
            create_layout()

        render_enzyme_list()

        with ui.row().classes('gap-2 items-end mt-2'):
            with ui.column().classes('gap-0'):
                ui.label('New Enzyme Name').classes('text-xs text-gray-600')
                new_enzyme_name_input['ref'] = ui.input(placeholder='e.g. BsmBI').classes('w-48')
            ui.button('Add Enzyme', icon='add', on_click=add_manual_enzyme)

        if len(enzyme_registry) > len(ENZYME_WELLS_POOL):
            ui.label(f'Warning: more enzymes tracked than the reagent plate has wells for ({len(ENZYME_WELLS_POOL)} max).').classes('text-orange-600 text-sm mt-2')

        ui.separator()

        ui.label('Step 6: Deck Layout').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Shows all 11 deck slots plus the actual wells for the parts '
                'rack, reagent plate, and reaction plate (Slot 7, thermocycler). '
                'Updates instantly.'
            ).classes('text-gray-500 text-sm')

        with ui.expansion('', icon='palette').classes('w-full'):
            ui.label(
                'Green = an Enzyme (each unique enzyme gets its own well). '
                'Blue = T4 Ligase. Purple = Buffer. Teal = Water. '
                'Orange = a DNA part. Pink = an assigned reaction. Gray = empty.'
            ).classes('text-gray-500 text-sm')

        ui.label(
            'Click any colored well below to see its details (reagent volumes, '
            'part usage, or reaction contents - parts, enzyme, and everything '
            'that goes into that specific reaction).'
        ).classes('text-blue-600 text-sm font-semibold')

        layout_container = ui.column().classes('w-full')

        PLATE_CELL_COLORS = {
            'bsai': '#c8e6c9', 'ligase': '#bbdefb', 'buffer': '#e1bee7',
            'water': '#b2dfdb', 'part': '#ffe0b2', 'reaction': '#f8bbd0', 'empty': '#e0e0e0',
        }

        def show_reaction_detail(row_data, well):
            detail = get_reaction_detail(row_data)

            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label(f"Reaction Well {detail['well']} ({detail['circuit_name']})").classes('text-lg font-bold')
                ui.separator()

                ui.label('Reagents (in mixing order):').classes('font-semibold text-sm mt-2')
                with ui.column().classes('gap-1 ml-2'):
                    for reagent in detail['reagents']:
                        ui.label(f"{reagent['name']} - Reagent Plate well {reagent['well']} - {reagent['volume_uL']} uL").classes('text-sm')

                ui.label('DNA Parts (added first):').classes('font-semibold text-sm mt-3')
                with ui.column().classes('gap-1 ml-2'):
                    if detail['parts']:
                        for part in detail['parts']:
                            ui.label(f"{part['name']} - Parts Rack well {part['well']} - {part['volume_uL']} uL").classes('text-sm')
                    else:
                        ui.label('No parts listed for this reaction.').classes('text-sm text-gray-400 italic')

                ui.button('Close', on_click=dialog.close).classes('mt-3')
            dialog.open()

        def show_reagent_detail(reagent_name, volume, well):
            with ui.dialog() as dialog, ui.card().classes('w-80'):
                ui.label(f'{reagent_name}').classes('text-lg font-bold')
                ui.separator()
                ui.label(f'Reagent Plate well: {well}').classes('text-sm mt-2')
                ui.label(f'Volume per reaction: {volume} uL').classes('text-sm')
                ui.label('Used in every reaction that uses this reagent.').classes('text-sm text-gray-500 mt-2')
                ui.button('Close', on_click=dialog.close).classes('mt-3')
            dialog.open()

        def show_part_detail(part_name, well):
            parts_col = find_parts_column()
            used_in = []
            if parts_col:
                for row in rows:
                    raw = row.get(parts_col, '')
                    row_parts = [p.strip() for p in str(raw).split(',') if p.strip()]
                    if part_name in row_parts:
                        label_col = column_headers[0] if column_headers else None
                        used_in.append(row.get(label_col, row.get('_reaction_well', '?')))

            with ui.dialog() as dialog, ui.card().classes('w-80'):
                ui.label(f'{part_name}').classes('text-lg font-bold')
                ui.separator()
                ui.label(f'Parts Rack well: {well}').classes('text-sm mt-2')
                ui.label(f'Volume per reaction: {part_volume.value} uL').classes('text-sm')
                if used_in:
                    ui.label(f'Used in: {", ".join(str(x) for x in used_in)}').classes('text-sm text-gray-500 mt-2')
                else:
                    ui.label('Not currently used in any reaction.').classes('text-sm text-gray-400 italic mt-2')
                ui.button('Close', on_click=dialog.close).classes('mt-3')
            dialog.open()

        def render_plate_grid(title, num_rows, num_cols, well_colors, on_reaction_click=None):
            row_letters = [chr(ord('A') + i) for i in range(num_rows)]
            with ui.column():
                ui.label(title).classes('text-md font-bold')
                with ui.grid(columns=num_cols + 1).classes('gap-1'):
                    ui.label('').classes('w-8 h-8')
                    for col in range(1, num_cols + 1):
                        ui.label(str(col)).classes('w-8 h-8 flex items-center justify-center font-bold text-xs')
                    for row_letter in row_letters:
                        ui.label(row_letter).classes('w-8 h-8 flex items-center justify-center font-bold text-xs')
                        for col in range(1, num_cols + 1):
                            well = f'{row_letter}{col}'
                            label, color_key = well_colors.get(well, ('', 'empty'))
                            bg = PLATE_CELL_COLORS[color_key]
                            display_text = label if label and len(str(label)) <= 6 else (str(label)[:5] + '...' if label else '')

                            clickable = on_reaction_click is not None and label
                            cell = ui.element('div').classes(
                                'w-8 h-8 flex items-center justify-center border border-gray-400 text-xs'
                            ).style(f'background-color: {bg}')
                            if clickable:
                                cell.classes('cursor-pointer hover:opacity-70')

                                def make_handler(w=well):
                                    def handler():
                                        on_reaction_click(w)
                                    return handler

                                cell.on('click', make_handler())
                            with cell:
                                ui.label(display_text if label else '').tooltip(str(label) if label else '')

        def create_layout():
            layout_container.clear()

            deck_labels = {n: 'Empty' for n in range(1, 12)}
            deck_labels[int(tiprack_slot_1.value)] = f'Tip Rack 1 (slot {tiprack_slot_1.value})'
            deck_labels[int(tiprack_slot_2.value)] = f'Tip Rack 2 (slot {tiprack_slot_2.value})'
            deck_labels[int(tiprack_slot_3.value)] = f'Tip Rack 3 (slot {tiprack_slot_3.value})'
            deck_labels[int(temp_module_slot.value)] = f'Temperature Module + Reagent Plate (slot {temp_module_slot.value})'
            deck_labels[int(parts_rack_slot.value)] = f'DNA Parts Rack (slot {parts_rack_slot.value})'
            for slot in [7, 10]:
                deck_labels[slot] = 'Thermocycler (96-Well Reaction Plate)' if slot == 7 else 'Thermocycler'

            with layout_container:
                with ui.grid(columns=3).classes('w-full gap-2'):
                    for slot_num in range(1, 12):
                        with ui.card().classes('p-2 text-center'):
                            ui.label(f'Slot {slot_num}').classes('font-bold text-sm')
                            ui.label(deck_labels.get(slot_num, 'Empty')).classes('text-xs text-gray-500')

                ui.separator().classes('my-4')

                with ui.row().classes('gap-4 items-center mb-2 flex-wrap'):
                    for key, label in [('bsai', 'Enzyme'), ('ligase', 'T4 Ligase'), ('buffer', 'Buffer'),
                                        ('water', 'Water'), ('part', 'DNA Part'), ('reaction', 'Assigned Circuit'), ('empty', 'Empty')]:
                        with ui.row().classes('items-center gap-1'):
                            ui.element('div').classes('w-4 h-4 border border-gray-400').style(f'background-color: {PLATE_CELL_COLORS[key]}')
                            ui.label(label).classes('text-xs')

                with ui.row().classes('gap-8 flex-wrap'):
                    enzyme_to_well = get_enzyme_to_well_map()
                    reagent_well_colors = {well: (name, 'bsai') for name, well in enzyme_to_well.items()}
                    reagent_well_colors[LIGASE_WELL] = ('T4 Ligase', 'ligase')
                    reagent_well_colors[BUFFER_WELL] = ('Buffer', 'buffer')
                    reagent_well_colors[WATER_WELL] = ('Water', 'water')

                    def handle_reagent_click(well):
                        label, _ = reagent_well_colors.get(well, ('', ''))
                        if well == LIGASE_WELL:
                            volume = ligase_volume.value
                        elif well == BUFFER_WELL:
                            volume = buffer_volume.value
                        elif well == WATER_WELL:
                            volume = max(0, total_volume.value - (enzyme_volume.value + ligase_volume.value + buffer_volume.value))
                        else:
                            volume = enzyme_volume.value
                        show_reagent_detail(label, volume, well)

                    render_plate_grid(
                        f'Reagent Plate (24-Well, Slot {temp_module_slot.value})', 4, 6,
                        reagent_well_colors, on_reaction_click=handle_reagent_click
                    )

                    parts_well_colors = {
                        PARTS_WELLS[i]: (p['name'], 'part')
                        for i, p in enumerate(parts_registry) if i < len(PARTS_WELLS)
                    }

                    def handle_part_click(well):
                        label, _ = parts_well_colors.get(well, ('', ''))
                        show_part_detail(label, well)

                    render_plate_grid(
                        f'DNA Parts Rack (24-Well, Slot {parts_rack_slot.value})', 4, 6,
                        parts_well_colors, on_reaction_click=handle_part_click
                    )

                    label_col = column_headers[0] if column_headers else None
                    reaction_well_colors = {}
                    overflow_count = 0
                    well_to_row = {}
                    if label_col:
                        for row in rows:
                            well = row.get('_reaction_well')
                            if well in REACTION_WELLS:
                                reaction_well_colors[well] = (row.get(label_col, ''), 'reaction')
                                well_to_row[well] = row
                            elif well == 'OUT OF WELLS':
                                overflow_count += 1

                    def handle_reaction_click(well):
                        row_data = well_to_row.get(well)
                        if row_data:
                            show_reaction_detail(row_data, well)

                    render_plate_grid(
                        'Reaction Plate (96-Well, Slot 7 - Thermocycler)', 8, 12,
                        reaction_well_colors, on_reaction_click=handle_reaction_click
                    )

                if overflow_count > 0:
                    ui.label(f'Warning: {overflow_count} reaction(s) have no well available.').classes('text-orange-600 text-sm mt-2')

                if len(get_unique_enzymes()) > len(ENZYME_WELLS_POOL):
                    ui.label(
                        f'Warning: {len(get_unique_enzymes())} unique enzymes found, but only '
                        f'{len(ENZYME_WELLS_POOL)} wells are available for enzymes on the reagent plate.'
                    ).classes('text-orange-600 text-sm mt-2')

        tiprack_slot_1.on_value_change(lambda: create_layout())
        tiprack_slot_2.on_value_change(lambda: create_layout())
        tiprack_slot_3.on_value_change(lambda: create_layout())
        temp_module_slot.on_value_change(lambda: create_layout())
        parts_rack_slot.on_value_change(lambda: create_layout())

        create_layout()
        ui.separator()

        ui.label('Step 7: Thermocycler Profile').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Included automatically in the generated protocol. Alternates '
                '~37C (enzyme cuts) and ~16C (ligase seals), then a final hot '
                'step (~60C) shuts enzymes off.'
            ).classes('text-gray-500 text-sm')

        with ui.column().classes('gap-0'):
            precool_checkbox = ui.checkbox('Pre-cool thermocycler block while reactions are pipetted in', value=True)
            precool_temp = ui.number('Pre-cool temp (C)', value=4).style('width: 200px')
        ui.label(
            'Robot keeps pipetting while the block cools, no time lost.'
        ).classes('text-gray-400 text-xs italic mt-1')

        with ui.column().classes('gap-0 mt-2'):
            capture_after_loading = ui.checkbox('Snapshot after reactions are loaded', value=False)
            capture_after_thermocycler = ui.checkbox('Snapshot after thermocycler run completes', value=False)
            capture_per_reaction = ui.checkbox('Snapshot after each reaction is loaded (stop-motion "recording")', value=False)
        ui.label(
            'OT-2 can\'t livestream, so this is not a live feed - it\'s stills '
            'saved on the robot, downloadable from the Opentrons App after the '
            'run. Per-reaction snapshots add real time (pauses to clear the '
            'pipette from view each shot).'
        ).classes('text-gray-400 text-xs italic')

        ui.separator()

        ui.label('Step 8: Generate Protocol').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Builds a real Opentrons protocol file. Order per reaction: '
                'DNA parts, then T4 ligase and buffer, then water, then enzyme '
                'added last, then a mix step (10 repetitions at 75% of total '
                'reaction volume). Runs the thermocycler after.'
            ).classes('text-gray-500 text-sm')

        generated_protocol = {'text': None}

        def generate_protocol():
            temp_slot = temp_module_slot.value
            tip_slot = tiprack_slot_1.value
            parts_slot = parts_rack_slot.value
            pipette_name = pipette_choice.value
            total_vol = total_volume.value

            reaction_steps = ''
            for row in rows:
                detail = get_reaction_detail(row)
                well = detail['well']

                part_steps = ''
                for part in detail['parts']:
                    if part['well'] != 'NO WELL ASSIGNED':
                        part_steps += f'''
    pipette.pick_up_tip()
    pipette.aspirate({part['volume_uL']}, parts_plate["{part['well']}"])
    pipette.dispense({part['volume_uL']}, reaction_plate["{well}"])
    pipette.drop_tip()
'''

                reagent_steps = ''
                for reagent in detail['reagents']:
                    if reagent['well'] != 'NO WELL ASSIGNED':
                        reagent_steps += f'''
    pipette.pick_up_tip()
    pipette.aspirate({reagent['volume_uL']}, reagent_plate["{reagent['well']}"])
    pipette.dispense({reagent['volume_uL']}, reaction_plate["{well}"])
    pipette.drop_tip()
'''

                mix_volume = round(total_vol * 0.75)
                mix_step = f'''
    pipette.pick_up_tip()
    pipette.mix(repetitions=3, volume={mix_volume}, location=reaction_plate["{well}"])
    pipette.drop_tip()
'''

                reaction_steps += part_steps + reagent_steps + mix_step
                if capture_per_reaction.value:
                    reaction_steps += f'    protocol.capture_image(home_before=True, filename="reaction_{well}")\n'

            # --- Step 7 options: pre-cool + camera snapshots ---
            do_precool = precool_checkbox.value
            precool_c = precool_temp.value

            precool_start_line = (
                f'    precool_task = thermocycler.start_set_block_temperature(temperature={precool_c})  '
                f'# non-blocking: cools while reactions are pipetted in\n'
                if do_precool else ''
            )
            precool_wait_line = (
                '    protocol.wait_for_tasks([precool_task])  # make sure the block hit temp before sealing\n'
                if do_precool else ''
            )

            # Real command now: deactivate outright, no reason to keep holding a temp.
            temp_module_post_line = (
                '    temp_module.deactivate()  # reagents already dispensed, no need to keep this cold\n'
            )

            capture_loaded_line = (
                '    protocol.capture_image(home_before=True, filename="reactions_loaded")\n'
                if capture_after_loading.value else ''
            )
            capture_done_line = (
                '    thermocycler.open_lid()  # lid must be open for the camera to see the plate\n'
                '    protocol.capture_image(home_before=True, filename="thermocycler_complete")\n'
                if capture_after_thermocycler.value else ''
            )

            protocol_text = f'''"""
Auto-generated Golden Gate / Loop Assembly protocol.
Reaction count: {len(rows)}
Mixing order: parts -> ligase/buffer -> water -> enzyme (last) -> mix
"""

from opentrons import protocol_api

metadata = {{
    "protocolName": "Golden Gate Assembly - Auto-generated",
    "author": "TransfectionWizard",
    "description": "Auto-generated one-pot Golden Gate/Loop assembly protocol",
}}

requirements = {{"robotType": "OT-2", "apiLevel": "2.27"}}


def run(protocol: protocol_api.ProtocolContext):
    thermocycler = protocol.load_module(module_name="thermocyclerModuleV2")
    reaction_plate = thermocycler.load_labware(name="nest_96_wellplate_100ul_pcr_full_skirt")

    temp_module = protocol.load_module(module_name="temperature module gen2", location="{temp_slot}")
    reagent_plate = temp_module.load_labware(name="opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    temp_module.set_temperature(celsius=4)

    parts_plate = protocol.load_labware(load_name="opentrons_24_tuberack_nest_1.5ml_snapcap", location="{parts_slot}")

    tiprack = protocol.load_labware(load_name="opentrons_96_tiprack_20ul", location="{tip_slot}")

    pipette = protocol.load_instrument(instrument_name="{pipette_name}", mount="left", tip_racks=[tiprack])

    thermocycler.open_lid()
    pipette.well_bottom_clearance.dispense = 10.5
    pipette.well_bottom_clearance.aspirate = -1
{precool_start_line}{reaction_steps}{capture_loaded_line}{precool_wait_line}    thermocycler.close_lid()
    thermocycler.set_lid_temperature(temperature=105)
{temp_module_post_line}
    profile = [
        {{"temperature": 37, "hold_time_seconds": 120}},
        {{"temperature": 16, "hold_time_seconds": 300}},
    ]
    thermocycler.set_block_temperature(temperature=37, hold_time_seconds=180)
    thermocycler.execute_profile(steps=profile, repetitions=30, block_max_volume={total_vol})
    thermocycler.set_block_temperature(temperature=50, hold_time_minutes=15)
    thermocycler.set_block_temperature(temperature=60, hold_time_minutes=10)
    thermocycler.set_block_temperature(temperature=4)
{capture_done_line}'''

            generated_protocol['text'] = protocol_text
            ui.download(protocol_text.encode('utf-8'), 'assembly_protocol.py')
            ui.notify('Protocol generated')
            simulate_button.enable()

        generate_button = ui.button('Generate OT-2 Protocol', icon='science', on_click=generate_protocol)
        generate_button.disable()

        def update_generate_button_state():
            generate_button.enable() if rows else generate_button.disable()

        ui.separator()

        ui.label('Step 9: Simulate Protocol').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label('Runs a real dry-run check using Opentrons\' own simulator.').classes('text-gray-500 text-sm')

        output_card = ui.card().classes('w-full').style('border: 2px solid #e2e8f0;')
        output_card.set_visibility(False)
        with output_card:
            ui.label('Simulation Output').classes('text-lg font-semibold')
            output_log = ui.log(max_lines=None).classes('w-full').style(
                'height: 400px; background-color: #1e293b; color: #e2e8f0; '
                'font-family: monospace; font-size: 12px; padding: 12px; '
                'overflow-y: auto; white-space: pre-wrap; word-wrap: break-word;'
            )

        async def handle_simulate():
            if not generated_protocol['text']:
                ui.notify('Generate a protocol first', type='warning')
                return
            output_log.clear()
            output_card.set_visibility(True)
            output_log.push('Running Opentrons simulation...\n')

            success, output = await asyncio.to_thread(run_opentrons_simulation, generated_protocol['text'])

            output_log.clear()
            output_log.push(output)
            if success:
                output_log.push('\n\n' + '=' * 60 + '\nSimulation completed successfully\n')
                ui.notify('Simulation completed successfully', type='positive')
            else:
                output_log.push('\n\n' + '=' * 60 + '\nSimulation failed\n')
                ui.notify('Simulation failed - see output below', type='negative')

        simulate_button = ui.button('Simulate Protocol', icon='play_arrow', on_click=handle_simulate)
        simulate_button.disable()

        ui.separator()

        ui.label('Step 10: Download Files').classes('text-lg font-semibold')
        with ui.expansion('', icon='help_outline').classes('w-full'):
            ui.label(
                'Downloads a record of this run: the reaction data, the '
                'protocol file, a visual plate layout spreadsheet, and a '
                'log showing exactly what went where. Generate a protocol above first.'
            ).classes('text-gray-500 text-sm')

        def build_reaction_csv() -> bytes:
            output = io.StringIO()
            if not rows:
                return b''
            fieldnames = list(column_headers) + ['reaction_well']
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                row_out = {h: row.get(h, '') for h in column_headers}
                row_out['reaction_well'] = row.get('_reaction_well', '')
                writer.writerow(row_out)
            return output.getvalue().encode('utf-8')

        def build_robot_log_json() -> bytes:
            log = {
                'reaction_count': len(rows),
                'pipette': pipette_choice.value,
                'tip_rack_slots': [tiprack_slot_1.value, tiprack_slot_2.value, tiprack_slot_3.value],
                'temperature_module_slot': temp_module_slot.value,
                'parts_rack_slot': parts_rack_slot.value,
                'total_reaction_volume_uL': total_volume.value,
                'thermocycler_profile': {
                    'cutting_temp_C': 37,
                    'sealing_temp_C': 16,
                    'cycles': 30,
                    'final_deactivation_temp_C': 60,
                    'final_deactivation_minutes': 5,
                },
                'parts_registry': parts_registry,
                'enzyme_to_well': get_enzyme_to_well_map(),
                'reactions': [get_reaction_detail(row) for row in rows],
            }
            return json_module.dumps(log, indent=2).encode('utf-8')

        def build_plate_layout_xlsx() -> bytes:
            try:
                import openpyxl
                from openpyxl.styles import PatternFill, Font, Alignment
            except ImportError:
                return b''

            wb = openpyxl.Workbook()
            wb.remove(wb.active)

            def write_plate_sheet(sheet_name, num_rows, num_cols, well_colors, color_map):
                ws = wb.create_sheet(sheet_name)
                row_letters = [chr(ord('A') + i) for i in range(num_rows)]
                for col in range(1, num_cols + 1):
                    ws.cell(row=1, column=col + 1, value=col).alignment = Alignment(horizontal='center')
                for i, row_letter in enumerate(row_letters):
                    ws.cell(row=i + 2, column=1, value=row_letter).font = Font(bold=True)
                    for col in range(1, num_cols + 1):
                        well = f'{row_letter}{col}'
                        label, color_key = well_colors.get(well, ('', 'empty'))
                        cell = ws.cell(row=i + 2, column=col + 1, value=label if label else '')
                        hex_color = color_map.get(color_key, 'E0E0E0').replace('#', '')
                        cell.fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type='solid')
                        cell.alignment = Alignment(horizontal='center')

            color_map = {k: v.replace('#', '') for k, v in PLATE_CELL_COLORS.items()}

            enzyme_to_well = get_enzyme_to_well_map()
            reagent_well_colors = {well: (name, 'bsai') for name, well in enzyme_to_well.items()}
            reagent_well_colors[LIGASE_WELL] = ('T4 Ligase', 'ligase')
            reagent_well_colors[BUFFER_WELL] = ('Buffer', 'buffer')
            reagent_well_colors[WATER_WELL] = ('Water', 'water')
            write_plate_sheet('Reagent Plate', 4, 6, reagent_well_colors, color_map)

            parts_well_colors = {
                PARTS_WELLS[i]: (p['name'], 'part')
                for i, p in enumerate(parts_registry) if i < len(PARTS_WELLS)
            }
            write_plate_sheet('DNA Parts Rack', 4, 6, parts_well_colors, color_map)

            label_col = column_headers[0] if column_headers else None
            reaction_well_colors = {}
            if label_col:
                for row in rows:
                    well = row.get('_reaction_well')
                    if well in REACTION_WELLS:
                        reaction_well_colors[well] = (row.get(label_col, ''), 'reaction')
            write_plate_sheet('Reaction Plate', 8, 12, reaction_well_colors, color_map)

            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            return buffer.read()

        def build_zip() -> bytes:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('reaction_config.csv', build_reaction_csv())
                if generated_protocol['text']:
                    zf.writestr('opentrons_protocol.py', generated_protocol['text'])
                xlsx_data = build_plate_layout_xlsx()
                if xlsx_data:
                    zf.writestr('plate_layouts.xlsx', xlsx_data)
                zf.writestr('robot_log.json', build_robot_log_json())
            zip_buffer.seek(0)
            return zip_buffer.read()

        download_options = [
            'All Files (.zip)',
            'Reaction Config (.csv)',
            'Opentrons Protocol (.py)',
            'Plate Layouts (.xlsx)',
            'Robot Log (.json)',
        ]
        default_filenames = {
            'All Files (.zip)': 'assembly_run',
            'Reaction Config (.csv)': 'reaction_config',
            'Opentrons Protocol (.py)': 'opentrons_protocol',
            'Plate Layouts (.xlsx)': 'plate_layouts',
            'Robot Log (.json)': 'robot_log',
        }

        with ui.row().classes('gap-4 items-end'):
            download_select = ui.select(
                download_options, value=download_options[0], label='Select Download'
            ).classes('w-64')

            filename_field = ui.input(
                label='Filename (without extension)', value=default_filenames[download_options[0]]
            ).classes('w-64')

            def on_download_option_change():
                filename_field.value = default_filenames[download_select.value]

            download_select.on_value_change(lambda: on_download_option_change())

            def trigger_download():
                if not rows:
                    ui.notify('Add at least one reaction first', type='warning')
                    return

                option = download_select.value
                filename = filename_field.value.strip() or default_filenames[option]

                if option == 'All Files (.zip)':
                    data = build_zip()
                    ui.download(data, f'{filename}.zip')
                elif option == 'Reaction Config (.csv)':
                    ui.download(build_reaction_csv(), f'{filename}.csv')
                elif option == 'Opentrons Protocol (.py)':
                    if not generated_protocol['text']:
                        ui.notify('Generate a protocol first (Step 8)', type='warning')
                        return
                    ui.download(generated_protocol['text'].encode('utf-8'), f'{filename}.py')
                elif option == 'Plate Layouts (.xlsx)':
                    data = build_plate_layout_xlsx()
                    if not data:
                        ui.notify('Excel export unavailable (openpyxl not installed)', type='negative')
                        return
                    ui.download(data, f'{filename}.xlsx')
                elif option == 'Robot Log (.json)':
                    ui.download(build_robot_log_json(), f'{filename}.json')

                ui.notify(f'Downloading {filename}...')

            ui.button('Download', on_click=trigger_download)