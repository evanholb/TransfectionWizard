"""Layout generation component."""

from typing import Callable
from nicegui import ui

from core.state import AppState, TemplateState
from core.validation import validate_experiment_design
from core.layout import generate_layout, generate_plate_layouts
from core.exporters import generate_excel_file, generate_opentrons_script
from core.config import DNA_ORIGIN, DILUTED_SOURCE, DNA_DESTINATION, TRANSFECTION_DESTINATION, PLATE_DESTINATION
from ui.components.table import confirm_action


async def handle_generate_layouts(
    state: AppState,
    templates: TemplateState,
    grid_manager,
    on_success: Callable
):
    """
    Generate plate layouts and outputs.

    Args:
        state: Application state
        templates: Template state
        grid_manager: Grid manager instance
        on_success: Callback to run after successful generation
    """
    # Sync grid data first
    if grid_manager.grid is not None:
        await grid_manager.sync()

    # Clear previous generated files
    state.clear_generated_files()

    # Check if data exists
    if not state.has_data():
        ui.notify('Please add data first', type='warning')
        on_success()
        return

    # Validate experiment design using detected layout
    is_valid, error_msg = validate_experiment_design(state.df, state.layout_key, state.labware_config)
    if not is_valid:
        # Show validation errors and clear visualization
        ui.notify('Validation failed - check errors below', type='negative')
        state.clear_generated_files()
        on_success(show_errors=error_msg)
        return

    # Generate layout
    try:
        # Use detected layout from template
        augmented_df = generate_layout(state.df, state.layout_key, state.labware_config)
        plate_layouts = generate_plate_layouts(augmented_df, state.layout_key, state.labware_config)
        excel_file = generate_excel_file(augmented_df, plate_layouts, state.layout_key, state.labware_config)

        # Get active template
        template_path, custom_content = templates.get_active_content()

        # Generate Opentrons script
        if custom_content:
            opentrons_script = generate_opentrons_script(
                augmented_df,
                custom_template_content=custom_content
            )
        else:
            opentrons_script = generate_opentrons_script(
                augmented_df,
                template_path=template_path
            )

        # Save to state
        state.config = augmented_df
        state.layouts = excel_file
        state.opentrons_script = opentrons_script

        # Update main dataframe with augmented data
        state.df = augmented_df

        # Success callback
        ui.notify('Layouts created successfully!', type='positive')
        on_success()

    except Exception as e:
        # Clear generated files and visualization on error
        state.clear_generated_files()
        ui.notify(f'Error creating layouts: {str(e)}', type='negative')
        on_success()


def has_layout_values(state: AppState) -> bool:
    """
    Check if any of the layout columns have values.

    Args:
        state: Application state

    Returns:
        True if any layout column has non-empty values
    """
    layout_columns = [DNA_ORIGIN, DILUTED_SOURCE, DNA_DESTINATION, TRANSFECTION_DESTINATION, PLATE_DESTINATION]

    for col in layout_columns:
        if col in state.df.columns:
            # Check for non-NA and non-empty string values
            has_values = state.df[col].apply(lambda x: x is not None and str(x).strip() != '').any()
            if has_values:
                return True
    return False


def create_layout_button(
    state: AppState,
    templates: TemplateState,
    grid_manager,
    on_success: Callable
):
    """
    Create layout generation button and reset button.

    Args:
        state: Application state
        templates: Template state
        grid_manager: Grid manager instance
        on_success: Callback after successful generation
    """
    # Container for buttons
    button_row = ui.row().classes('gap-2')

    with button_row:
        # Create Layout button
        async def handle_click():
            await handle_generate_layouts(state, templates, grid_manager, on_success)

        ui.button('Create Layout', on_click=handle_click).style(
            'background-color: #50C878 !important; color: white !important;'
        )

        # Reset Layout button (conditionally shown)
        reset_button_container = ui.row().classes('gap-0')

        def update_reset_button():
            """Show/hide reset button based on layout column values"""
            reset_button_container.clear()
            if has_layout_values(state):
                with reset_button_container:
                    async def handle_reset():
                        if await confirm_action(
                            'This will reset all layout assignments (DNA Origin, Diluted Source, DNA Destination, Transfection Destination, Plate Destination). Are you sure?',
                            'Reset Layout'
                        ):
                            count = await grid_manager.reset_layout_columns()
                            on_success()
                            update_reset_button()
                            ui.notify(
                                f'Layout reset ({count} cells cleared)',
                                type='positive'
                            )

                    ui.button(
                        'Reset Layout',
                        icon='refresh',
                        on_click=handle_reset
                    ).props('flat').tooltip('Clear all layout columns')

        # Initial button state
        update_reset_button()

        # Return update function so it can be called after layout generation
        return update_reset_button
