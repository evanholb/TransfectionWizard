"""Table component for experiment data editing."""

from typing import Callable
from nicegui import ui
import pandas as pd

from core.state import AppState
from core.config import (
    ALL_COLUMNS,
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    TRANSFECTION_TYPE,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION
)
from ui.components.grid_manager import GridManager


async def confirm_action(message: str, title: str = "Confirm") -> bool:
    """Show confirmation dialog and return user's choice."""
    result = {'confirmed': False}

    with ui.dialog() as dialog, ui.card():
        ui.label(title).classes('text-lg font-bold')
        ui.label(message)
        with ui.row().classes('gap-2'):
            ui.button('Cancel', on_click=dialog.close).props('flat')

            async def confirm():
                result['confirmed'] = True
                dialog.close()

            ui.button('Confirm', on_click=confirm).props('color=negative')

    await dialog
    return result['confirmed']


def create_table_section(state: AppState, on_data_changed: Callable, rebuild_upload=None, clear_viz=None):
    """
    Create table editing UI section.

    Args:
        state: Application state
        on_data_changed: Callback when data changes
        rebuild_upload: Optional callback to rebuild upload button
        clear_viz: Optional callback to clear visualizations
    """
    # Create grid manager
    grid_manager = GridManager(state)

    # Container for table
    table_container = ui.column().classes('w-full')

    def update_table():
        """Rebuild the table UI."""
        table_container.clear()

        with table_container:
            # Column placeholders/tooltips
            placeholders = {
                CIRCUIT_NAME: 'e.g., Circuit1',
                TRANSFECTION_GROUP: 'e.g., X1',
                DNA_PART_NAME: 'e.g., mKO2',
                CONCENTRATION: 'ng/μL',
                QUANTITY_DNA: 'ng',
                DNA_ORIGIN: 'e.g., A1.1 (auto-filled if empty)',
                DNA_DESTINATION: 'e.g., B1.1 (auto-filled if empty)',
                TRANSFECTION_DESTINATION: 'e.g., C1.1 (auto-filled if empty)',
                PLATE_DESTINATION: 'e.g., A1.1 (auto-filled if empty)'
            }

            # Always display ALL_COLUMNS (even if empty)
            display_cols = ALL_COLUMNS

            # Build column definitions
            columns = []
            for col in display_cols:
                placeholder = placeholders.get(col, '')
                col_def = {
                    'field': col,
                    'headerName': col,
                    'headerTooltip': placeholder,
                }
                columns.append(col_def)

            # Convert dataframe to records
            rows = state.df.to_dict('records')

            # Create AG Grid
            grid_manager.grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': rows,
                'rowSelection': 'multiple',
                'stopEditingWhenCellsLoseFocus': True,
                'defaultColDef': {
                    'editable': True,
                    'sortable': True,
                    'filter': True,
                },
            }).classes('w-full').style('height: 400px')

            # Cell change handler
            async def on_cell_changed(e):
                await grid_manager.sync()
                on_data_changed()

            grid_manager.grid.on('cellValueChanged', on_cell_changed)

            # Action buttons
            with ui.row().classes('gap-2 items-center mt-2'):
                # Add row button
                async def handle_add_row():
                    await grid_manager.add_row()
                    ui.notify('Row added - click cells to edit', type='positive')
                    update_table()
                    on_data_changed()

                ui.button('Add Row', icon='add', on_click=handle_add_row).props('color=primary')

                # Delete selected button (conditionally shown)
                delete_selected_container = ui.row().classes('gap-0')

                async def handle_delete_selected():
                    count = await grid_manager.delete_selected()
                    if count > 0:
                        ui.notify(f'Deleted {count} row(s)', type='positive')
                        update_table()
                        on_data_changed()
                    else:
                        ui.notify('No rows selected', type='warning')

                async def update_delete_button(e):
                    selected = await grid_manager.grid.get_selected_rows()
                    delete_selected_container.clear()
                    with delete_selected_container:
                        if selected and len(selected) > 0:
                            ui.button(
                                'Delete Selected',
                                icon='delete',
                                on_click=handle_delete_selected
                            ).props('flat color=negative')

                grid_manager.grid.on('selectionChanged', update_delete_button)

                # Delete all button (only shown if table has data)
                if len(state.df) > 0:
                    async def handle_delete_all():
                        if await confirm_action(
                            f'This will permanently delete all {len(state.df)} rows. Are you sure?',
                            'Delete All Data'
                        ):
                            count = await grid_manager.delete_all(rebuild_upload)
                            ui.notify(f'All data cleared ({count} rows)', type='info')
                            update_table()
                            on_data_changed()
                            if clear_viz:
                                clear_viz()

                    ui.button(
                        'Delete All',
                        icon='delete_sweep',
                        on_click=handle_delete_all
                    ).props('flat color=negative').tooltip('Clear entire table')

                # Circuit deletion controls
                if CIRCUIT_NAME in state.df.columns:
                    circuits = sorted([
                        str(c) for c in state.df[CIRCUIT_NAME].unique()
                        if pd.notna(c) and str(c).strip()
                    ])
                    if circuits:
                        ui.label('Delete circuit:').classes('ml-4')
                        circuit_select = ui.select(
                            circuits,
                            label='Select Circuit'
                        ).classes('w-48')

                        async def handle_delete_circuit():
                            circuit = circuit_select.value
                            if not circuit:
                                ui.notify('Please select a circuit', type='warning')
                                return

                            count = await grid_manager.delete_circuit(circuit, rebuild_upload)
                            if count > 0:
                                ui.notify(
                                    f'Deleted circuit "{circuit}" ({count} rows)',
                                    type='positive'
                                )
                                update_table()
                                on_data_changed()

                                if clear_viz:
                                    clear_viz()
                            else:
                                ui.notify(f'Circuit "{circuit}" not found', type='warning')

                        ui.button(
                            'Delete',
                            icon='delete_forever',
                            on_click=handle_delete_circuit
                        ).props('flat color=negative')

    # Initial table render
    update_table()

    # Return update function so other components can refresh table
    return update_table
