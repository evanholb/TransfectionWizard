"""Visualization section component."""

from nicegui import ui

from core.state import AppState
from ui.components.plate_renderer import PlateRenderer


def create_visualization_section(state: AppState):
    """
    Create visualization UI section.

    Args:
        state: Application state

    Returns:
        Tuple of (container, update_function)
    """
    viz_container = ui.column().classes('w-full')

    def update_visualizations(show_errors: str = None):
        """
        Update visualization display.

        Args:
            show_errors: If provided, display error message instead of plates
        """
        viz_container.clear()

        # Show validation errors if provided
        if show_errors:
            with viz_container:
                ui.label('Validation Failed').classes('text-lg font-bold text-red-600')
                ui.label('Please fix the following issues before generating layout:').classes(
                    'text-sm text-gray-600 mt-2'
                )
                with ui.column().classes('mt-4 p-4 bg-red-50 rounded border border-red-200'):
                    for line in show_errors.split('\n'):
                        if line.strip():
                            ui.label(line).classes('text-sm text-red-800')
            return

        # Show plate layouts if available
        if state.has_generated_files():
            with viz_container:
                # Create fresh renderer instance each time to avoid state caching issues
                renderer = PlateRenderer()
                renderer.render_all_plates(state)

    return viz_container, update_visualizations
