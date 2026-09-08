"""Build tab - main experiment design interface."""

import os
import pandas as pd
from nicegui import ui

from core.state import AppState, TemplateState
from core.config import CIRCUIT_NAME, TRANSFECTION_GROUP, DNA_PART_NAME
from ui.components import upload, table, layout_gen, visualization, download, simulation
from ui.components.grid_manager import GridManager


# Dictionary mapping exact ERN or Target names to their extracted image file paths
ERN_IMAGE_MAP = {
    # ERN Proteins
    'CSY4': 'static/images/csy4_protein.png',
    'CASE': 'static/images/case_protein.png',
    'PGU': 'static/images/pgu_protein.png',
    
    # ERN Target Sites
    'Csy4 target site': 'static/images/csy4_target.png',
    'CasE target site': 'static/images/case_target.png',
    'PgU target site': 'static/images/pgu_target.png',
}


def extract_variable_label(part_name: str) -> str:
    """Extract variable label text following 'rec_' in the part name."""
    if not part_name:
        return ""
    if 'rec_' in part_name:
        return part_name.split('rec_', 1)[1]
    elif 'rec' in part_name.lower():
        idx = part_name.lower().find('rec')
        sub = part_name[idx + 3:]
        return sub.lstrip('_- ')
    return part_name


def get_ern_info(dna_part: str, row: pd.Series = None) -> dict:
    """Classify part into ERN protein or ERN target site and assign the extracted image path."""
    part_str = str(dna_part) if pd.notna(dna_part) else ""
    part_upper = part_str.strip().upper()
    exact_erns = {'CSY4': 'Csy4', 'CASE': 'CasE', 'PGU': 'PgU'}

    # ERN Protein match
    if part_upper in exact_erns:
        main_label = exact_erns[part_upper]
        image_path = ERN_IMAGE_MAP.get(part_upper, 'static/images/default_ern.png')
        return {
            'type': 'ERN',
            'main_label': main_label,
            'image_path': image_path,
            'variable_label': None
        }

    # ERN Target Site match
    var_label = extract_variable_label(part_str)
    part_lower = part_str.lower()

    if 'csy4' in part_lower:
        site_label = 'Csy4 target site'
    elif 'case' in part_lower:
        site_label = 'CasE target site'
    elif 'pgu' in part_lower:
        site_label = 'PgU target site'
    else:
        site_label = 'Target site'
        if row is not None:
            row_str = ' '.join([str(v) for v in row.values if pd.notna(v)]).lower()
            if 'csy4' in row_str:
                site_label = 'Csy4 target site'
            elif 'case' in row_str:
                site_label = 'CasE target site'
            elif 'pgu' in row_str:
                site_label = 'PgU target site'

    image_path = ERN_IMAGE_MAP.get(site_label, 'static/images/default_target.png')

    return {
        'type': 'ERN_TARGET',
        'main_label': site_label,
        'image_path': image_path,
        'variable_label': var_label
    }


def create_build_tab(state: AppState, templates: TemplateState):
    """Create the Build tab interface."""
    with ui.column().classes('w-full gap-4'):
        grid_manager = GridManager(state)

        callbacks = {
            'update_table': None,
            'update_viz': None,
            'rebuild_upload': None,
            'update_simulation': None,
            'update_circuit_viz': None
        }

        def on_data_changed():
            state.clear_generated_files()

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

        def clear_generated_ui():
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

        # Table section
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
            
            if df is None or df.empty or CIRCUIT_NAME not in df.columns or DNA_PART_NAME not in df.columns:
                ui.label(
                    f'Please upload or enter data with "{CIRCUIT_NAME}" and "{DNA_PART_NAME}" columns to view visualizations.'
                ).classes('text-gray-500 italic')
                return

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

                exact_erns = ['PgU', 'CasE', 'Csy4']
                circuit_df = df[df[CIRCUIT_NAME].astype(str) == selected_circuit]

                def matches_ern(val):
                    val_str = str(val) if pd.notna(val) else ''
                    return val_str in exact_erns or 'rec' in val_str.lower()

                matching_df = circuit_df[circuit_df[DNA_PART_NAME].apply(matches_ern)]

                with filtered_container:
                    if matching_df.empty:
                        ui.label(
                            f'No matching ERN rows found for circuit "{selected_circuit}".'
                        ).classes('text-gray-500 italic mt-2')
                        return

                    # Single outer container card forming 1 Big Figure
                    with ui.card().classes('w-full p-6 bg-white border border-slate-300 rounded-2xl shadow-sm'):
                        ui.label(f'Circuit Diagram: {selected_circuit}').classes('text-xl font-bold text-slate-800 border-b border-slate-200 pb-3 mb-4 w-full')

                        # Determine all Transfection Groups
                        if TRANSFECTION_GROUP in matching_df.columns:
                            groups = matching_df[TRANSFECTION_GROUP].fillna('Ungrouped').unique()
                        else:
                            groups = ['Ungrouped']

                        # Render all groups side by side in 1 row (or flex wrap)
                        with ui.row().classes('w-full gap-8 flex-wrap items-start justify-start'):
                            for group in sorted(groups):
                                if group == 'Ungrouped' and TRANSFECTION_GROUP in matching_df.columns:
                                    group_df = matching_df[matching_df[TRANSFECTION_GROUP].isna()]
                                elif TRANSFECTION_GROUP in matching_df.columns:
                                    group_df = matching_df[matching_df[TRANSFECTION_GROUP] == group]
                                else:
                                    group_df = matching_df

                                ern_items = []
                                target_items = []

                                for _, row in group_df.iterrows():
                                    info = get_ern_info(row[DNA_PART_NAME], row=row)
                                    info['row'] = row
                                    if info['type'] == 'ERN':
                                        ern_items.append(info)
                                    else:
                                        target_items.append(info)

                                # Column section for each Transfection Group inside the big figure
                                with ui.column().classes('gap-4 p-4 rounded-xl bg-slate-50/60 border border-slate-100 min-w-[240px]'):
                                    ui.label(f'Group: {group}').classes('text-md font-bold text-slate-700 bg-slate-200/70 px-3 py-1 rounded-md self-start')

                                    # Render Smaller Uncased ERN Proteins
                                    if ern_items:
                                        ui.label('Proteins').classes('text-xs font-semibold text-slate-500 uppercase tracking-wider')
                                        with ui.column().classes('gap-3 items-center w-full'):
                                            for item in ern_items:
                                                with ui.column().classes('items-center gap-1 p-1 w-full'):
                                                    if os.path.exists(item['image_path']):
                                                        ui.image(item['image_path']).classes('w-16 h-auto max-w-full object-contain')
                                                    else:
                                                        ui.icon('image_not_supported', size='32px').classes('text-slate-400')
                                                    ui.label(item['main_label']).classes('text-sm font-semibold text-slate-800 text-center')

                                    # Render Uncased ERN Target Sites
                                    if target_items:
                                        ui.label('Targets').classes('text-xs font-semibold text-slate-500 uppercase tracking-wider mt-2')
                                        with ui.column().classes('gap-3 items-center w-full'):
                                            for item in target_items:
                                                with ui.column().classes('items-center gap-1 p-1 w-full'):
                                                    if os.path.exists(item['image_path']):
                                                        ui.image(item['image_path']).classes('w-36 h-auto max-w-full object-contain')
                                                    else:
                                                        ui.icon('image_not_supported', size='40px').classes('text-slate-400')
                                                    
                                                    ui.label(item['main_label']).classes('text-sm font-semibold text-slate-800 text-center')
                                                    
                                                    var_text = item['variable_label'] if item['variable_label'] else 'N/A'
                                                    ui.label(f"Var: {var_text}").classes('text-xs text-slate-500 font-mono text-center')

            # Render Dropdown
            ui.select(
                options=circuits,
                label='Select Circuit',
                on_change=on_circuit_select
            ).classes('w-64')

        render_visualize_section()
        callbacks['update_circuit_viz'] = render_visualize_section.refresh
        ui.separator()

        # Layout section
        ui.label('Experiment Layout').classes('text-xl font-bold')

        def on_layout_success(show_errors=None):
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

        _, callbacks['update_viz'] = visualization.create_visualization_section(state)
        ui.separator()

        # Simulation section
        ui.label('Opentrons Simulation').classes('text-xl font-bold')
        callbacks['update_simulation'] = simulation.create_simulation_section(state)
        ui.separator()

        # Download section
        download.create_download_section(state, templates)