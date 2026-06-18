"""Plate layout visualization component."""

from typing import Set
import pandas as pd
from nicegui import ui

from core.state import AppState
from core.config import (
    PLATE_COLORS,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    DILUTED_SOURCE,
    CIRCUIT_NAME
)
from core.layout import generate_plate_layouts


class PlateRenderer:
    """
    Renders plate layouts with color coding.

    Replaces the complex inline rendering logic from main.py:384-421
    with a clean, reusable component.
    """

    def __init__(self):
        # Add # prefix to colors for CSS
        self.colors = {k: f'#{v}' for k, v in PLATE_COLORS.items()}

    def render_all_plates(self, state: AppState):
        """
        Render all input racks and output plate visualizations.

        Args:
            state: Application state containing config dataframe
        """
        if not state.has_generated_files():
            return

        # Generate plate layouts with detected layout
        plate_layouts = generate_plate_layouts(state.config, state.layout_key, state.labware_config)

        # Get sets for color determination
        dna_parts = set(state.config[DNA_ORIGIN].unique())
        destinations = (
            set(state.config[DNA_DESTINATION].unique()) |
            set(state.config[TRANSFECTION_DESTINATION].unique())
        )

        # Track diluted sources separately for distinct coloring
        diluted_sources = set()
        if DILUTED_SOURCE in state.config.columns:
            diluted_sources = set(state.config[DILUTED_SOURCE].dropna().unique())
            diluted_sources.discard('')  # Remove empty strings

        # Render input racks in a row
        with ui.row().classes('gap-4 mt-4 flex-wrap'):
            for name in sorted(plate_layouts.keys()):
                if 'input_rack' in name:
                    layout_df = plate_layouts[name]
                    with ui.column():
                        self.render_plate(name, layout_df, dna_parts, destinations, diluted_sources, state)

        # Render output plates in a row
        with ui.row().classes('gap-4 mt-8 flex-wrap'):
            for name in sorted(plate_layouts.keys()):
                if 'output_plate' in name:
                    layout_df = plate_layouts[name]
                    with ui.column():
                        self.render_plate(name, layout_df, dna_parts, destinations, diluted_sources, state)

    def render_plate(
        self,
        name: str,
        layout_df: pd.DataFrame,
        dna_parts: Set[str],
        destinations: Set[str],
        diluted_sources: Set[str],
        state: AppState = None
    ):
        """
        Render a single plate layout.

        Args:
            name: Sheet name (e.g., 'input_rack_1', 'output_plate')
            layout_df: DataFrame with plate layout
            dna_parts: Set of DNA part slot positions
            destinations: Set of destination slot positions
            diluted_sources: Set of diluted source slot positions
            state: Application state (to check layout type)
        """
        # Get the rack/plate index
        parts = name.split('_')
        idx = int(parts[-1])

        # Determine display name based on layout and position
        if 'input_rack' in name:
            if state and state.layout_key == '96well':
                # 96well layout: slots 4&5 = 24-tube racks, slot 6 = 96-well plate
                if idx == 1:
                    display_name = f'Input #{idx}: 24-Tube Rack (OT-2 Slot 4)'
                elif idx == 2:
                    display_name = f'Input #{idx}: 24-Tube Rack (OT-2 Slot 5)'
                elif idx == 3:
                    display_name = f'Input #{idx}: 96-Well Plate (OT-2 Slot 6)'
                else:
                    display_name = f'Input #{idx}: Input Rack (OT-2 Slot {idx + 3})'
            else:
                # 24tube layout: all are 24-tube racks in slots 4, 5, 6
                slot_num = idx + 3
                display_name = f'Input #{idx}: 24-Tube Rack (OT-2 Slot {slot_num})'
        elif 'output_plate' in name:
            # Output plates in slots 2 and 3
            slot_num = idx + 1
            display_name = f'Output #{idx}: 24-Well Plate (OT-2 Slot {slot_num})'
        else:
            display_name = name.replace('_', ' ').title()

        ui.label(display_name).classes('text-lg font-bold')

        # Grid layout - columns = number of data columns + 1 for row labels
        # Determine if this is a 96-well plate (8 rows or 12 columns)
        is_96well = len(layout_df.index) == 8 or len(layout_df.columns) == 12

        num_cols = len(layout_df.columns) + 1
        with ui.grid(columns=num_cols).classes('gap-1'):
            self._render_headers(layout_df, is_96well)
            self._render_rows(name, layout_df, dna_parts, destinations, diluted_sources, is_96well)

    def _render_headers(self, layout_df: pd.DataFrame, is_96well: bool = False):
        """Render column headers for the plate."""
        # Adjust sizes for 96-well plates
        cell_size = 'w-6 h-6' if is_96well else 'w-8 h-8'
        text_size = 'text-xs'

        # Empty corner cell
        ui.label('').classes(cell_size)

        # Column numbers
        for col in layout_df.columns:
            ui.label(str(col)).classes(
                f'{cell_size} flex items-center justify-center font-bold {text_size}'
            )

    def _render_rows(
        self,
        sheet_name: str,
        layout_df: pd.DataFrame,
        dna_parts: Set[str],
        destinations: Set[str],
        diluted_sources: Set[str],
        is_96well: bool = False
    ):
        """Render all rows of the plate."""
        # Adjust sizes for 96-well plates
        cell_size = 'w-6 h-6' if is_96well else 'w-8 h-8'
        text_size = 'text-xs'

        for row_label in layout_df.index:
            # Row label
            ui.label(row_label).classes(
                f'{cell_size} flex items-center justify-center font-bold {text_size}'
            )

            # Row cells
            for col in layout_df.columns:
                value = layout_df.loc[row_label, col]
                color = self._get_cell_color(
                    value, sheet_name, row_label, col, dna_parts, destinations, diluted_sources
                )
                self._render_cell(value, color, is_96well)

    def _get_cell_color(
        self,
        value: str,
        sheet_name: str,
        row: str,
        col: int,
        dna_parts: Set[str],
        destinations: Set[str],
        diluted_sources: Set[str]
    ) -> str:
        """
        Determine cell background color based on value and position.

        Args:
            value: Cell content
            sheet_name: Name of the sheet/plate
            row: Row label (A, B, C, D)
            col: Column number
            dna_parts: Set of DNA part positions
            destinations: Set of destination positions
            diluted_sources: Set of diluted source positions

        Returns:
            Hex color code with # prefix
        """
        if not value:
            return self.colors['empty']

        if 'output_plate' in sheet_name:
            return self.colors['circuit']

        # For input racks, determine color based on slot position
        rack_num = sheet_name.split('_')[-1]
        full_slot = f"{row}{col}.{rack_num}"

        if full_slot in dna_parts:
            return self.colors['dna_part']
        elif full_slot in diluted_sources:
            return self.colors['diluted_source']
        elif full_slot in destinations:
            return self.colors['destination']
        elif value in ['Reserved', 'H2O', 'L3K/P3K Mix', 'P3000', 'Opti-MEM', 'L3000', 'L3000/OM Mix', 'P3000/OM Mix','Empty tube']:
            return self.colors['reagent']
        else:
            return self.colors['empty']

    def _render_cell(self, value: str, bg_color: str, is_96well: bool = False):
        """
        Render a single plate cell.

        Args:
            value: Cell content
            bg_color: Background color (hex with # prefix)
            is_96well: Whether this is a 96-well plate (smaller cells)
        """
        # Adjust sizes for 96-well plates
        if is_96well:
            cell_size = 'w-8 h-8'
            text_size = 'text-xs'
            max_chars = 3
        else:
            cell_size = 'w-12 h-12'
            text_size = 'text-xs'
            max_chars = 6

        # Truncate long values for display
        cell_text = value if value and len(str(value)) <= max_chars else \
                   (str(value)[:max_chars-1] + '...' if value else '')

        # Render cell div
        with ui.element('div').classes(
            f'{cell_size} flex items-center justify-center '
            f'border border-gray-400 {text_size}'
        ).style(f'background-color: {bg_color}'):
            if value:
                ui.label(cell_text).tooltip(str(value))
            else:
                ui.label('')
