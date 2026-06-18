"""Build tab - main experiment design interface."""

from nicegui import ui

from core.state import AppState, TemplateState
from ui.components import upload, table, layout_gen, visualization, download, simulation
from ui.components.grid_manager import GridManager


def create_build_tab(state: AppState, templates: TemplateState):
    """
    Create the Build tab interface.

    Orchestrates all components: upload, table, layout generation, visualization, and download.

    Args:
        state: Application state
        templates: Template state
    """
    with ui.column().classes('w-full gap-4'):
        grid_manager = GridManager(state)

        # Callbacks dict for deferred initialization
        callbacks = {'update_table': None, 'update_viz': None, 'rebuild_upload': None, 'update_simulation': None}

        def on_data_changed():
            """Callback when data changes - clear generated files and refresh UI"""
            # Clear all generated files since table data changed
            state.clear_generated_files()

            # Refresh UI components
            if callbacks['update_table']:
                callbacks['update_table']()
            if callbacks.get('update_reset_button'):
                callbacks['update_reset_button']()
            if callbacks['update_viz']:
                callbacks['update_viz']()
            if callbacks['update_simulation']:
                callbacks['update_simulation']()
            if hasattr(state, '_update_predict_circuits'):
                state._update_predict_circuits()
            if hasattr(state, '_clear_prediction'):
                state._clear_prediction()

        # Define callback to clear generated UI (viz + simulation)
        def clear_generated_ui():
            """Clear both visualization and simulation UI when data changes"""
            if callbacks['update_viz']:
                callbacks['update_viz']()
            if callbacks['update_simulation']:
                callbacks['update_simulation']()

        # Upload section
        callbacks['rebuild_upload'] = upload.create_upload_section(
            state, templates, grid_manager, on_data_changed, clear_generated_ui
        )
        ui.separator()

        # Table section (pass callbacks dict so it can clear viz later)
        callbacks['update_table'] = table.create_table_section(
            state,
            on_data_changed,
            callbacks['rebuild_upload'],
            clear_viz=clear_generated_ui
        )
        ui.separator()

        # Experiment Layout section (button + visualization)
        ui.label('Experiment Layout').classes('text-xl font-bold')

        def on_layout_success(show_errors=None):
            """Callback after layout generation"""
            if callbacks['update_table']:
                callbacks['update_table']()
            if callbacks['update_viz']:
                callbacks['update_viz'](show_errors=show_errors)
            if callbacks['update_simulation']:
                callbacks['update_simulation']()
            if callbacks.get('update_reset_button'):
                callbacks['update_reset_button']()

        callbacks['update_reset_button'] = layout_gen.create_layout_button(
            state, templates, grid_manager, on_layout_success
        )

        # Visualization (no title, already part of Experiment Layout section)
        _, callbacks['update_viz'] = visualization.create_visualization_section(state)
        ui.separator()

        # Opentrons Simulation section
        ui.label('Opentrons Simulation').classes('text-xl font-bold')
        callbacks['update_simulation'] = simulation.create_simulation_section(state)
        ui.separator()

        # Download section
        download.create_download_section(state, templates)
