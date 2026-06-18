"""Opentrons protocol simulation component."""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from nicegui import ui

from core.state import AppState


def run_opentrons_simulation(script_content: str) -> tuple[bool, str]:
    """
    Run Opentrons protocol simulation on a script.

    Args:
        script_content: Python script content to simulate

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        # Write script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_path = f.name

        try:
            # Run simulation
            result = subprocess.run(
                ['opentrons_simulate', temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += f"\n\nStderr:\n{result.stderr}"

            success = result.returncode == 0

            return success, output

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    except FileNotFoundError:
        return False, ("Error: opentrons_simulate command not found.\n\n"
                      "Please install the Opentrons Python package:\n"
                      "  pip install opentrons\n\n"
                      "Or install via conda:\n"
                      "  conda install -c bioconda opentrons")
    except subprocess.TimeoutExpired:
        return False, "Error: Simulation timed out (>30 seconds)"
    except Exception as e:
        return False, f"Error running simulation: {str(e)}"


def create_simulation_section(state: AppState):
    """
    Create the simulation section with button and output display.

    Args:
        state: Application state
    """
    # Container for the entire simulation section
    with ui.column().classes('w-full gap-2') as section:

        # References for dynamic updates
        simulate_button = None
        output_log = None
        output_card = None

        async def handle_simulate():
            """Handle simulation button click"""
            if not state.opentrons_script:
                ui.notify('Please create layout first', type='warning')
                return

            # Clear and show output
            output_log.clear()
            output_card.set_visibility(True)
            output_log.push("Running Opentrons simulation...\n")

            try:
                # Run simulation in background thread to not block UI
                success, output = await asyncio.to_thread(
                    run_opentrons_simulation,
                    state.opentrons_script
                )

                # Update output
                output_log.clear()

                # Show simulation output first
                output_log.push(output)

                # Then show status at the bottom for easy visibility
                if success:
                    output_log.push("\n\n" + "=" * 60 + "\n")
                    output_log.push("✓ Simulation completed successfully\n")
                    # Store with success indicator at bottom for later display
                    state.simulation_output = f"{output}\n\n{'=' * 60}\n✓ Simulation completed successfully"
                else:
                    output_log.push("\n\n" + "=" * 60 + "\n")
                    output_log.push("✗ Simulation failed\n")
                    # Store with failure indicator at bottom for later display
                    state.simulation_output = f"{output}\n\n{'=' * 60}\n✗ Simulation failed"

                # Notify user
                if success:
                    ui.notify('Simulation completed successfully', type='positive')
                else:
                    ui.notify('Simulation failed - see output below', type='negative')

            except Exception as e:
                output_log.clear()
                output_log.push(f"Error: {str(e)}")
                ui.notify(f'Simulation error: {str(e)}', type='negative')

            finally:
                update_button_state()

        def update_button_state():
            """Update button state based on whether script exists"""
            has_script = state.opentrons_script is not None

            # Show previous output if exists
            if state.simulation_output and has_script:
                output_card.set_visibility(True)
                output_log.clear()
                # Output already includes success/failure indicator
                output_log.push(state.simulation_output)
            else:
                output_card.set_visibility(False)

        # Create UI elements
        simulate_button = ui.button('Simulate', on_click=handle_simulate)

        with ui.column().classes('w-full'):
            with ui.card().classes('w-full').style('border: 2px solid #e2e8f0;') as output_card:
                ui.label('Simulation Output').classes('text-lg font-semibold')

                # Scrollable log output
                output_log = ui.log(max_lines=None).classes('w-full').style(
                    'height: 400px; '
                    'background-color: #1e293b; '
                    'color: #e2e8f0; '
                    'font-family: monospace; '
                    'font-size: 12px; '
                    'padding: 12px; '
                    'overflow-y: auto; '
                    'white-space: pre-wrap; '
                    'word-wrap: break-word;'
                )

        update_button_state()

        return update_button_state
