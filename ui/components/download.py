"""Download functionality component - replaces repetitive download logic."""

import base64
import zipfile
from io import BytesIO
from nicegui import ui

from core.state import AppState, TemplateState
from core.config import ALL_COLUMNS
from core.json_converter import convert_to_json


class DownloadHandler:
    """
    Handles file downloads with strategy pattern.

    Replaces the large if/elif blocks in main.py:464-536 with
    clean, testable strategy methods.
    """

    def __init__(self, state: AppState, templates: TemplateState):
        self.state = state
        self.templates = templates

        # Strategy mapping
        self.strategies = {
            'All Files (.zip)': (self.generate_zip, '.zip', 'application/zip'),
            'Experiment Config (.csv)': (self.generate_csv, '.csv', 'text/csv'),
            'Opentrons Script (.py)': (self.generate_script, '.py', 'text/x-python'),
            'Plate Layouts (.xlsx)': (self.generate_excel, '.xlsx',
                                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            'Biocompiler Format (.json5)': (self.generate_biocompiler_json, '.json5', 'application/json'),
        }

    async def download(self, option: str, filename: str):
        """
        Trigger download for selected option.

        Args:
            option: Download option (e.g., 'All Files (.zip)')
            filename: Base filename without extension
        """
        # Biocompiler Format doesn't require generated files, just data
        if option == 'Biocompiler Format (.json5)':
            if not self.state.has_data():
                ui.notify('Please upload or add data first', type='warning')
                return
        elif not self.state.has_generated_files():
            ui.notify('Please create layout first', type='warning')
            return

        if not filename.strip():
            ui.notify('Please enter a filename', type='warning')
            return

        try:
            # Get strategy for this option
            generator, extension, mime_type = self.strategies[option]

            # Generate file data
            data_bytes = generator()

            # Trigger browser download
            await self._save_file(data_bytes, f"{filename}{extension}", mime_type)

            ui.notify(f'Saving {filename}{extension}...', type='positive')

        except Exception as e:
            ui.notify(f'Download error: {str(e)}', type='negative')

    def generate_zip(self) -> bytes:
        """Generate zip file containing all outputs."""
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add CSV config
            config_df = self.state.config[ALL_COLUMNS]
            csv_data = config_df.to_csv(index=False)
            zip_file.writestr('experiment_config.csv', csv_data)

            # Add Opentrons script
            zip_file.writestr('opentrons_protocol.py', self.state.opentrons_script)

            # Add Excel layouts
            self.state.layouts.seek(0)
            excel_data = self.state.layouts.read()
            zip_file.writestr('plate_layouts.xlsx', excel_data)

            # Add Biocompiler JSON5 format
            json_data = self.generate_biocompiler_json()
            zip_file.writestr('biocompiler_format.json5', json_data)

        zip_buffer.seek(0)
        return zip_buffer.read()

    def generate_csv(self) -> bytes:
        """Generate CSV configuration file."""
        # Ensure columns are in ALL_COLUMNS order
        config_df = self.state.config[ALL_COLUMNS]
        csv_data = config_df.to_csv(index=False)
        return csv_data.encode()

    def generate_script(self) -> bytes:
        """Generate Opentrons Python script."""
        return self.state.opentrons_script.encode()

    def generate_excel(self) -> bytes:
        """Generate Excel plate layouts."""
        self.state.layouts.seek(0)
        return self.state.layouts.read()

    def generate_biocompiler_json(self) -> bytes:
        """Generate Biocompiler JSON5 format from current data."""
        # Use state.df (the working data) instead of state.config
        json_str = convert_to_json(self.state.df)
        return json_str.encode()

    async def _save_file(self, data_bytes: bytes, filename: str, mime_type: str):
        """
        Trigger browser file save dialog.

        Args:
            data_bytes: File content
            filename: Filename with extension
            mime_type: MIME type for the file
        """
        data_base64 = base64.b64encode(data_bytes).decode('utf-8')

        await ui.run_javascript(f'''
            saveFileWithDialog("{data_base64}", "{filename}", "{mime_type}")
                .then(success => {{
                    if (!success) {{
                        console.log("Save cancelled");
                    }}
                }})
                .catch(err => console.error("Save error:", err));
        ''', timeout=30.0)


def create_download_section(state: AppState, templates: TemplateState):
    """
    Create download UI section.

    Args:
        state: Application state
        templates: Template state
    """
    ui.label('Download').classes('text-xl font-semibold')

    download_options = [
        'All Files (.zip)',
        'Experiment Config (.csv)',
        'Opentrons Script (.py)',
        'Plate Layouts (.xlsx)',
        'Biocompiler Format (.json5)'
    ]

    # Default filenames for each option
    default_filenames = {
        'All Files (.zip)': 'neuromorphic_experiment',
        'Experiment Config (.csv)': 'experiment_config',
        'Opentrons Script (.py)': 'opentrons_protocol',
        'Plate Layouts (.xlsx)': 'plate_layouts',
        'Biocompiler Format (.json5)': 'biocompiler_format',
    }

    handler = DownloadHandler(state, templates)

    # State for UI selections
    selected_download = {'option': download_options[0]}
    filename_input = {'value': default_filenames[download_options[0]]}

    def handle_download_change(e):
        """Update filename when download option changes."""
        selected_download['option'] = e.value
        filename_input['value'] = default_filenames[e.value]
        filename_field.value = default_filenames[e.value]

    def handle_filename_change(e):
        """Update filename state when user types."""
        filename_input['value'] = e.value

    async def trigger_download():
        """Trigger the download."""
        await handler.download(selected_download['option'], filename_input['value'])

    # Download UI row
    with ui.row().classes('gap-4 items-end'):
        ui.select(
            download_options,
            value=download_options[0],
            label='Select Download',
            on_change=handle_download_change
        ).classes('w-64')

        filename_field = ui.input(
            label='Filename (without extension)',
            value=default_filenames[download_options[0]],
            on_change=handle_filename_change
        ).classes('w-64')

        ui.button('Download', on_click=trigger_download)
