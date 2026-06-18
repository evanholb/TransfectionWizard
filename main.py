"""Neuromorphic Wizard - Main UI Application

Web interface for neuromorphic circuit experiment design and automation.
"""

from nicegui import ui

from core.state import AppState, TemplateState
from ui.tabs import build, predict, generate, analyze


def load_static_assets():
    """Load CSS and JavaScript files."""
    with open('static/js/file_operations.js', 'r') as f:
        ui.add_head_html(f'<script>{f.read()}</script>')

    with open('static/css/styles.css', 'r') as f:
        ui.add_head_html(f'<style>{f.read()}</style>')


@ui.page('/')
def main():
    """
    Main application entry point.

    Creates state, loads assets, and orchestrates tab creation.
    """
    state = AppState()
    templates = TemplateState()

    # Load static assets
    load_static_assets()

    # Header banner with navigation tabs
    with ui.row().classes('w-full items-center justify-between').style(
        'background: linear-gradient(90deg, #2b6cb0 0%, #4299e1 100%); '
        'padding: 15px 20px; '
        'box-shadow: 0 2px 4px rgba(0,0,0,0.1); '
        'margin: 0;'
    ):
        ui.label('Transfection Wizard').classes('text-3xl font-bold').style(
            'color: white; '
            'text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'
        )

        # Create tab navigation inside header
        with ui.tabs().style('color: white;') as tabs:
            build_tab = ui.tab('Design')
            predict_tab = ui.tab('Predict')
            generate_tab = ui.tab('Generate')
            analyze_tab = ui.tab('Analyze')

    # Create tab panels
    with ui.tab_panels(tabs, value=build_tab).classes('w-full').style('padding: 20px;'):
        with ui.tab_panel(build_tab):
            build.create_build_tab(state, templates)

        with ui.tab_panel(predict_tab):
            predict.create_predict_tab(state)

        with ui.tab_panel(generate_tab):
            generate.create_generate_tab()

        with ui.tab_panel(analyze_tab):
            analyze.create_analyze_tab()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Transfection Wizard', port=8080)
