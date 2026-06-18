"""State management for the application."""

from dataclasses import dataclass, field
from typing import Optional, Dict
import pandas as pd
from io import BytesIO

from .config import ALL_COLUMNS


@dataclass
class AppState:
    """
    Central application state for experiment design and generated outputs.

    Attributes:
        df: Main experiment design dataframe
        config: Generated configuration with all slots assigned
        layouts: Excel file with plate layouts (BytesIO)
        opentrons_script: Generated Opentrons Python script
        layout_key: Current layout type ('24tube' or '96well')
        labware_config: Dictionary mapping slot numbers to labware types from template
        simulation_output: Output from last Opentrons protocol simulation
    """
    df: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=ALL_COLUMNS))
    config: Optional[pd.DataFrame] = None
    layouts: Optional[BytesIO] = None
    opentrons_script: Optional[str] = None
    layout_key: str = '24tube'
    labware_config: Optional[Dict[str, str]] = None
    simulation_output: Optional[str] = None

    def has_data(self) -> bool:
        """Check if any experiment data exists."""
        return self.df is not None and len(self.df) > 0

    def has_generated_files(self) -> bool:
        """Check if layouts have been generated."""
        return self.config is not None

    def clear_generated_files(self):
        """Clear all generated files."""
        self.config = None
        self.layouts = None
        self.opentrons_script = None
        self.simulation_output = None

    def clear_all(self):
        """Clear all data including experiment design."""
        self.df = pd.DataFrame(columns=ALL_COLUMNS)
        self.clear_generated_files()


@dataclass
class TemplateState:
    """
    Template management state for built-in and custom Opentrons scripts.

    Attributes:
        built_in: Built-in template files mapping
        custom: User-uploaded custom templates
        active: Currently selected template name
    """
    built_in: Dict[str, str] = field(default_factory=lambda: {
        'v3.8': 'data/OT2_automated_transfection_v3.8.py',
        'v3.9': 'data/OT2_automated_transfection_v3.9.py',
        '96-well': 'data/OT2_automated_transfection_test96well_format.py'
    })
    custom: Dict[str, str] = field(default_factory=dict)
    active: str = 'v3.9'

    def add_custom(self, filename: str, content: str):
        """Add a custom template and make it active."""
        self.custom[filename] = content
        self.active = filename

    def get_options(self) -> list:
        """Get list of all available template names."""
        return list(self.built_in.keys()) + list(self.custom.keys())

    def get_active_content(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get the active template content.

        Returns:
            Tuple of (template_path, custom_content)
            - If built-in: (path, None)
            - If custom: (None, content)
        """
        if self.active in self.custom:
            return None, self.custom[self.active]
        elif self.active in self.built_in:
            return self.built_in[self.active], None
        else:
            # Fallback to default
            return self.built_in['v3.9'], None
