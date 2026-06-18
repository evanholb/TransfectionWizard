"""AG Grid state management - eliminates repetitive sync code."""

import pandas as pd
from typing import Optional
from nicegui import ui

from core.state import AppState
from core.utils import normalize_dataframe
from core.config import (
    ALL_COLUMNS,
    CONCENTRATION,
    QUANTITY_DNA,
    CIRCUIT_NAME,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    DILUTED_SOURCE,
    PLATE_DESTINATION
)


class GridManager:
    """
    Manages AG Grid state synchronization with AppState.

    Replaces the repetitive sync_grid_to_dataframe() calls scattered
    throughout the original code with a clean, centralized manager.
    """

    def __init__(self, state: AppState):
        self.state = state
        self.grid: Optional[ui.aggrid] = None

    async def sync(self):
        """Sync grid data back to state dataframe."""
        if self.grid is None:
            return

        try:
            rows = await self.grid.get_client_data()
            if rows and len(rows) > 0:
                df = pd.DataFrame(rows)
                self.state.df = normalize_dataframe(df)
            else:
                self.state.df = pd.DataFrame(columns=ALL_COLUMNS)
        except Exception as e:
            # Grid not ready yet - this is expected during initialization
            pass

    async def add_row(self):
        """
        Add a new empty row to the grid.

        Returns:
            Updated dataframe
        """
        await self.sync()

        # Create new row with appropriate defaults for ALL_COLUMNS
        new_row = {}
        for col in ALL_COLUMNS:
            # Numeric columns get None, text columns get empty string
            if col in [CONCENTRATION, QUANTITY_DNA]:
                new_row[col] = None
            else:
                new_row[col] = ''

        new_row_df = pd.DataFrame([new_row])
        self.state.df = pd.concat(
            [self.state.df, new_row_df],
            ignore_index=True
        )

        return self.state.df

    async def delete_selected(self) -> int:
        """
        Delete selected rows from grid.

        Returns:
            Number of rows deleted
        """
        await self.sync()

        if self.grid is None:
            return 0

        selected = await self.grid.get_selected_rows()
        if not selected:
            return 0

        # Convert selected rows to DataFrame for comparison
        selected_df = pd.DataFrame(selected)
        original_count = len(self.state.df)

        # Find matching rows to delete
        indices_to_drop = []
        for sel_row in selected:
            for idx, row in self.state.df.iterrows():
                match = True
                for col in self.state.df.columns:
                    df_val = row[col]
                    sel_val = sel_row.get(col)

                    # Handle None/NaN/empty string comparisons
                    if pd.isna(df_val) and (
                        sel_val is None or
                        sel_val == '' or
                        (isinstance(sel_val, float) and pd.isna(sel_val))
                    ):
                        continue
                    elif df_val != sel_val:
                        match = False
                        break

                if match:
                    indices_to_drop.append(idx)
                    break

        if indices_to_drop:
            self.state.df = self.state.df.drop(indices_to_drop).reset_index(drop=True)

        return len(indices_to_drop)

    async def delete_all(self, rebuild_upload=None) -> int:
        """
        Delete all rows from the grid.

        Args:
            rebuild_upload: Optional callback to rebuild upload button

        Returns:
            Number of rows deleted
        """
        await self.sync()
        row_count = len(self.state.df)
        self.state.clear_all()
        if rebuild_upload:
            rebuild_upload()
        return row_count

    async def delete_circuit(self, circuit_name: str, rebuild_upload=None) -> int:
        """
        Delete all rows for a given circuit.

        Args:
            circuit_name: Name of circuit to delete
            rebuild_upload: Optional callback to rebuild upload button

        Returns:
            Number of rows deleted
        """
        await self.sync()

        if CIRCUIT_NAME not in self.state.df.columns:
            return 0

        original_count = len(self.state.df)
        self.state.df = self.state.df[self.state.df[CIRCUIT_NAME] != circuit_name]
        deleted_count = original_count - len(self.state.df)

        # Clear generated files when deleting circuits (layout no longer valid)
        if deleted_count > 0:
            self.state.clear_generated_files()

        return deleted_count

    async def reset_layout_columns(self) -> int:
        """
        Clear the auto-assigned layout columns.

        Returns:
            Number of cells cleared
        """
        await self.sync()

        layout_columns = [DNA_ORIGIN, DILUTED_SOURCE, DNA_DESTINATION, TRANSFECTION_DESTINATION, PLATE_DESTINATION]

        # Count non-empty cells before clearing
        non_empty_count = 0
        for col in layout_columns:
            if col in self.state.df.columns:
                non_empty_count += self.state.df[col].notna().sum()

        # Clear the layout columns (set to empty string)
        for col in layout_columns:
            if col in self.state.df.columns:
                self.state.df[col] = ''

        # Clear generated files since layout is invalidated
        self.state.clear_generated_files()

        return non_empty_count
