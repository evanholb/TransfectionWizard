"""Generate tab - AI circuit designer placeholder."""

from nicegui import ui


def create_generate_tab():
    """Create the Generate tab interface (placeholder)."""
    with ui.column().classes('w-full h-64 items-center justify-center'):
        ui.label('AI Agent Interface to Biocompiler-Designer').classes(
            'text-2xl font-bold text-gray-400'
        )
        ui.label('[coming soon]').classes('text-lg text-gray-300')
