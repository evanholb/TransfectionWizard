"""Analyze tab - flow cytometry analyzer placeholder."""

from nicegui import ui


def create_analyze_tab():
    """Create the Analyze tab interface (placeholder)."""
    with ui.column().classes('w-full h-64 items-center justify-center'):
        ui.label('Flow Cytometry Results Visualizer').classes(
            'text-2xl font-bold text-gray-400'
        )
        ui.label('[coming soon]').classes('text-lg text-gray-300')
