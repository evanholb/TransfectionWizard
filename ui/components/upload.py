"""Upload component for experiment resources."""

import pandas as pd
from io import StringIO
from typing import Callable
from nicegui import ui

from core.state import AppState, TemplateState
from core.utils import normalize_dataframe
from core.config import ALL_COLUMNS, PLATE_DESTINATION, DNA_DESTINATION, detect_layout_from_labware
from core.script_utils import extract_csv_from_script, validate_ot2_labware, extract_labware_config
from core.layout import infer_circuits, infer_groups
from core.json_converter import parse_json


async def handle_upload(
    e,
    state: AppState,
    templates: TemplateState,
    grid_manager,
    on_data_changed: Callable
):
    """
    Handle file upload

    Args:
        e: Upload event
        state: Application state
        templates: Template state
        grid_manager: Grid manager for syncing
        on_data_changed: Callback to refresh UI after data changes
    """
    if grid_manager and grid_manager.grid is not None:
        try:
            await grid_manager.sync()
        except Exception as e:
            pass

    content = await e.file.text()
    filename = e.file.name
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''

    csv_content = None
    is_python_script = file_extension == 'py'
    is_json_file = file_extension in ['json', 'json5']

    # Handle JSON/JSON5 upload
    if is_json_file:
        try:
            df = parse_json(content)
        except ValueError as ex:
            ui.notify(f'Error parsing JSON: {str(ex)}', type='negative')
            return
        except Exception as ex:
            ui.notify(f'Failed to read JSON: {str(ex)}', type='negative')
            return

        # Normalize dataframe to ensure all columns exist in correct order
        df = normalize_dataframe(df)

        # Append to existing data
        if state.has_data():
            state.df = pd.concat([state.df, df], ignore_index=True)
        else:
            state.df = df

        # Notify and refresh UI
        ui.notify(f'Added {len(df)} row(s) from JSON', type='positive')
        on_data_changed()
        return

    # Handle Python script upload
    if is_python_script:
        if 'csv_raw' not in content or ("'''" not in content and '"""' not in content):
            ui.notify('Script must contain csv_raw with triple quotes', type='negative')
            return

        csv_content, error = extract_csv_from_script(content)
        if error:
            ui.notify(f'Error: {error}', type='negative')
            return

        # Extract labware configuration and detect layout
        labware_config, labware_error = extract_labware_config(content)
        if not labware_error and labware_config:
            try:
                detected_layout = detect_layout_from_labware(labware_config)
                state.layout_key = detected_layout
                state.labware_config = labware_config
            except ValueError as e:
                ui.notify(f'Layout validation error: {str(e)}', type='negative', multi_line=True)
                return

        # Add as custom template
        templates.add_custom(filename, content)
        ui.notify(f'Template added: {filename}', type='positive')

        # Update template selector if it exists
        if hasattr(templates, '_selector') and templates._selector is not None:
            templates._selector.options = templates.get_options()
            templates._selector.value = templates.active
            templates._selector.update()

    else:
        # Handle CSV upload
        csv_content = content

    # Process CSV content
    if not csv_content or not csv_content.strip():
        if is_python_script:
            return  # Already added as template
        ui.notify('CSV is empty', type='negative')
        return

    try:
        df = pd.read_csv(StringIO(csv_content))
    except Exception as ex:
        if is_python_script:
            return  # Already added as template
        ui.notify(f'Failed to read CSV: {str(ex)}', type='negative')
        return

    if df.empty:
        if is_python_script:
            return  # Already added as template
        ui.notify('CSV is empty', type='negative')
        return

    # Normalize dataframe to ensure all columns exist in correct order
    df = normalize_dataframe(df)

    # Infer circuit names and groups from location columns if not provided
    if PLATE_DESTINATION in df.columns:
        df = infer_circuits(df)
    if DNA_DESTINATION in df.columns:
        df = infer_groups(df)

    # Append to existing data
    if state.has_data():
        state.df = pd.concat([state.df, df], ignore_index=True)
    else:
        state.df = df

    # Notify and refresh UI
    ui.notify(f'Added {len(df)} row(s)', type='positive')
    on_data_changed()


def create_upload_section(
    state: AppState,
    templates: TemplateState,
    grid_manager,
    on_data_changed: Callable,
    clear_generated_ui: Callable = None
):
    """
    Create upload UI section.

    Args:
        state: Application state
        templates: Template state
        grid_manager: Grid manager for syncing
        on_data_changed: Callback when data changes
        clear_generated_ui: Optional callback to clear visualization and simulation UI

    Returns:
        Function to rebuild upload button
    """
    ui.label('Experiment Design').classes('text-xl font-bold')

    # Row container for upload button and template selector
    row_container = ui.row().classes('w-full items-center gap-4')

    # Container for upload button (can be refreshed)
    with row_container:
        upload_container = ui.column()

    def rebuild_upload_button():
        """Recreate the upload button (needed after deleting all data)."""
        upload_container.clear()
        with upload_container:
            ui.upload(
                label='Upload File (.csv, .json, .py)',
                on_upload=lambda e: handle_upload(e, state, templates, grid_manager, on_data_changed),
                auto_upload=True
            ).classes('w-[275px]').props('accept=".csv,.py,.json,.json5"')

    # Initial creation
    rebuild_upload_button()

    def on_template_change(e):
        """Handle template selection and detect layout."""
        templates.active = e.value

        # Clear any previously generated layouts/simulations since template changed
        state.clear_generated_files()
        if clear_generated_ui:
            clear_generated_ui()

        # Detect layout from selected template
        template_path, custom_content = templates.get_active_content()

        if custom_content:
            # Custom template - extract labware from content
            labware_config, _ = extract_labware_config(custom_content)
        elif template_path:
            # Built-in template - read file and extract labware
            try:
                with open(template_path, 'r') as f:
                    template_content = f.read()
                labware_config, _ = extract_labware_config(template_content)
            except Exception:
                labware_config = None
        else:
            labware_config = None

        if labware_config:
            try:
                detected_layout = detect_layout_from_labware(labware_config)
                state.layout_key = detected_layout
                state.labware_config = labware_config
            except ValueError as e:
                ui.notify(f'Layout validation error: {str(e)}', type='negative', multi_line=True)

    # OT-2 Template selector
    with row_container:
        ui.label('OT-2 Template:').classes('ml-4')
        template_selector = ui.select(
            templates.get_options(),
            value=templates.active,
            on_change=on_template_change
        ).classes('w-[200px]')

    # Store reference for template updates
    templates._selector = template_selector

    # Detect initial layout from default template
    on_template_change(type('obj', (), {'value': templates.active})())

    return rebuild_upload_button
