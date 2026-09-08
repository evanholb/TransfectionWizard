"""Build tab - main experiment design interface."""

import pandas as pd
from nicegui import ui

from core.state import AppState, TemplateState
from core.config import CIRCUIT_NAME, TRANSFECTION_GROUP, DNA_PART_NAME
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
        callbacks = {
            'update_table': None,
            'update_viz': None,
            'rebuild_upload': None,
            'update_simulation': None,
            'update_circuit_viz': None
        }

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
            if callbacks['update_circuit_viz']:
                callbacks['update_circuit_viz']()
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
            if callbacks['update_circuit_viz']:
                callbacks['update_circuit_viz']()

        # Upload section
        callbacks['rebuild_upload'] = upload.create_upload_section(
            state, templates, grid_manager, on_data_changed, clear_generated_ui
        )
        ui.separator()

        # Table section (Experiment Design)
        callbacks['update_table'] = table.create_table_section(
            state,
            on_data_changed,
            callbacks['rebuild_upload'],
            clear_viz=clear_generated_ui
        )
        ui.separator()

        # Visualize section
        ui.label('Visualize').classes('text-xl font-bold')

        @ui.refreshable
        def render_visualize_section():
            df = getattr(state, 'df', None)
            
            # Check for DataFrame and necessary column presence using config constants
            if df is None or df.empty or CIRCUIT_NAME not in df.columns or DNA_PART_NAME not in df.columns:
                ui.label(
                    f'Please upload or enter data with "{CIRCUIT_NAME}" and "{DNA_PART_NAME}" columns to view visualizations.'
                ).classes('text-gray-500 italic')
                return

            # Extract unique non-empty circuit names
            circuits = sorted([
                str(c) for c in df[CIRCUIT_NAME].dropna().unique()
                if str(c).strip()
            ])

            if not circuits:
                ui.label('No circuit data available.').classes('text-gray-500 italic')
                return

            filtered_container = ui.column().classes('w-full')

            def on_circuit_select(e):
                selected_circuit = e.value
                filtered_container.clear()

                if not selected_circuit:
                    return

                # Target ERN conditions
                exact_erns = ['PgU', 'CasE', 'Csy4']

                # Filter rows for selected circuit
                circuit_df = df[df[CIRCUIT_NAME].astype(str) == selected_circuit]

                # Filter function checking DNA_PART_NAME column for ERN matches
                def matches_ern(val):
                    val_str = str(val) if pd.notna(val) else ''
                    return val_str in exact_erns or 'rec' in val_str.lower()

                matching_df = circuit_df[circuit_df[DNA_PART_NAME].apply(matches_ern)]

                with filtered_container:
                    if matching_df.empty:
                        ui.label(
                            f'No matching ERN rows found for circuit "{selected_circuit}".'
                        ).classes('text-gray-500 italic mt-2')
                    else:
                        ui.label(f'Filtered ERNs and ERN targets for Circuit: {selected_circuit}').classes('text-md font-semibold mt-2')
                        
                        # Specify target display columns
                        target_cols = [TRANSFECTION_GROUP, DNA_PART_NAME]
                        
                        # Subset dataframe to only available target columns
                        display_cols = [col for col in target_cols if col in matching_df.columns]
                        subset_df = matching_df[display_cols]

                        columns = [{'name': col, 'label': col, 'field': col} for col in subset_df.columns]
                        records = subset_df.to_dict('records')
                        ui.table(columns=columns, rows=records).classes('w-full mt-2')

            # Render Dropdown
            ui.select(
                options=circuits,
                label='Select Circuit',
                on_change=on_circuit_select
            ).classes('w-64')

        render_visualize_section()
        callbacks['update_circuit_viz'] = render_visualize_section.refresh
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
