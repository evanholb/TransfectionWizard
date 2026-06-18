"""Predict tab - circuit prediction interface."""

import json
import numpy as np
import matplotlib.pyplot as plt
import httpx
from nicegui import ui

from core.state import AppState
from core.config import CIRCUIT_NAME
from core.json_converter import convert_to_biocompiler_recipe

# API Configuration
BIOCOMPILER_API_BASE = "https://biocomp-api.rachael.jdisset.com"
PREDICT_ENDPOINT = f"{BIOCOMPILER_API_BASE}/v1/predict/heatmap"


async def fetch_prediction(recipe: dict, resolution: int = 32) -> dict:
    """
    Make API call to biocomp-server and return prediction data.

    Args:
        recipe: Circuit recipe in biocompiler format
        resolution: Grid resolution (NxN)

    Returns:
        API response containing heatmap and metadata
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            PREDICT_ENDPOINT,
            json={"recipe": recipe, "resolution": resolution}
        )
        response.raise_for_status()
        return response.json()


def create_prediction_heatmap(matrix_data, circuit_name: str):
    """
    Create a heatmap visualization inside the current matplotlib context.

    Args:
        matrix_data: 2D list/array of prediction values
        circuit_name: Name of the circuit for the title
    """
    matrix = np.array(matrix_data)

    # Create heatmap with blue colormap
    im = plt.imshow(matrix, cmap='Blues', aspect='auto', origin='lower')

    # Add colorbar
    cbar = plt.colorbar(im, shrink=0.8)
    cbar.set_label('Prediction Value', fontsize=10)

    # Set axis labels (X1 for x-axis, X2 for y-axis)
    plt.xlabel('X1', fontsize=12)
    plt.ylabel('X2', fontsize=12)

    # Set title to circuit name
    plt.title(circuit_name, fontsize=12, fontweight='bold')

    # Remove axis ticks
    plt.xticks([])
    plt.yticks([])

    plt.tight_layout()


def create_predict_tab(state: AppState):
    """
    Create the Predict tab interface.

    Args:
        state: Application state
    """
    with ui.column().classes('w-full gap-4'):
        ui.label('Predict Circuit with Biocompiler-Predict').classes('text-xl font-bold')

        def get_circuits():
            """Get available circuit names from state."""
            if state.has_data() and CIRCUIT_NAME in state.df.columns:
                return sorted(state.df[CIRCUIT_NAME].unique().tolist())
            return []

        circuits = get_circuits()
        selected = {'circuit': circuits[0] if circuits else None}

        output_container_ref = {'container': None}

        def display_recipe_json(recipe: dict):
            """Helper to display the recipe JSON section."""
            ui.label('Recipe JSON').classes('text-lg font-semibold mt-4 mb-2')
            recipe_json = json.dumps(recipe, indent=2)
            ui.code(recipe_json).classes('w-[650px]').style(
                'max-height: 600px; overflow-y: auto; white-space: pre;'
            )

        async def plot_circuit():
            if selected['circuit']:
                # Show loading state
                output_container_ref['container'].clear()
                with output_container_ref['container']:
                    ui.label('Fetching prediction from Biocompiler...').classes('text-gray-500')
                    spinner = ui.spinner(size='lg')

                recipe = None

                try:
                    # Convert circuit to biocompiler recipe format
                    recipe = convert_to_biocompiler_recipe(state.df, selected['circuit'])

                    # Call the prediction API
                    response = await fetch_prediction(recipe, resolution=32)

                    # Extract heatmap data
                    heatmap_data = response["heatmap"]["z"]
                    timings = response["meta"]["timings_ms"]
                    model_name = response["meta"].get("model_signature", "unknown")

                    # Display results in UI
                    output_container_ref['container'].clear()
                    with output_container_ref['container']:
                        # Display heatmap visualization
                        with ui.pyplot(close=True, figsize=(6, 5)):
                            create_prediction_heatmap(heatmap_data, selected['circuit'])

                        # Display timing info
                        ui.label(
                            f"Model: {model_name} | Time: {timings['total']:.0f}ms"
                        ).classes('text-sm text-gray-500 mt-2')

                        # Display JSON recipe below
                        display_recipe_json(recipe)

                    ui.notify(
                        f"Prediction completed in {timings['total']:.0f}ms",
                        type='positive'
                    )

                except httpx.ConnectError:
                    output_container_ref['container'].clear()
                    with output_container_ref['container']:
                        ui.label('Error: Cannot connect to Biocompiler server').classes('text-red-500')
                        ui.label(f'Server URL: {BIOCOMPILER_API_BASE}').classes('text-gray-500 text-sm')
                        if recipe:
                            display_recipe_json(recipe)
                    ui.notify('Cannot connect to Biocompiler server', type='negative')

                except httpx.TimeoutException:
                    output_container_ref['container'].clear()
                    with output_container_ref['container']:
                        ui.label('Error: Request timed out (prediction may take too long)').classes('text-red-500')
                        if recipe:
                            display_recipe_json(recipe)
                    ui.notify('Request timed out', type='negative')

                except httpx.HTTPStatusError as e:
                    output_container_ref['container'].clear()
                    with output_container_ref['container']:
                        ui.label(f'Error: Server returned {e.response.status_code}').classes('text-red-500')
                        try:
                            detail = e.response.json().get('detail', str(e))
                        except Exception:
                            detail = str(e)
                        ui.label(f'Details: {detail}').classes('text-gray-500 text-sm')
                        if recipe:
                            display_recipe_json(recipe)
                    ui.notify(f'Server error: {e.response.status_code}', type='negative')

                except Exception as e:
                    output_container_ref['container'].clear()
                    with output_container_ref['container']:
                        ui.label(f"Error: {str(e)}").classes('text-red-500')
                        if recipe:
                            display_recipe_json(recipe)
                    ui.notify(f"Error: {str(e)}", type='negative')
            else:
                ui.notify('Please select a circuit', type='warning')

        with ui.row().classes('gap-4 items-center'):
            circuit_select = ui.select(
                circuits if circuits else ['No data uploaded'],
                value=selected['circuit'] if circuits else None,
                label='Select Circuit',
                on_change=lambda e: selected.update({'circuit': e.value})
            ).classes('w-64')

            ui.button('Predict', on_click=plot_circuit)

        output_container_ref['container'] = ui.column().classes('w-full')

        # Store update function for refreshing from build tab
        def update_circuits():
            circuits = get_circuits()
            circuit_select.options = circuits if circuits else ['No data uploaded']
            if circuits:
                circuit_select.value = circuits[0]
                selected['circuit'] = circuits[0]
            else:
                circuit_select.value = 'No data uploaded'
                selected['circuit'] = None
            circuit_select.update()

        state._update_predict_circuits = update_circuits

        # Store clear function for use when data changes in build tab
        def clear_prediction():
            if output_container_ref['container']:
                output_container_ref['container'].clear()

        state._clear_prediction = clear_prediction
