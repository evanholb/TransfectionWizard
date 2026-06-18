"""Data normalization and processing utilities."""

from contextlib import contextmanager
from typing import List, Union
import pandas as pd


def normalize_column_name(col: str) -> str:
    """Normalize column name to lowercase with underscores."""
    return col.strip().lower().replace(' ', '_')


def normalize_for_comparison(value) -> str:
    """
    Normalize a value for case-insensitive, whitespace-insensitive comparison.

    Used for grouping and validation operations on Contents, Circuit name,
    and Transfection group fields.

    Args:
        value: The value to normalize (can be string, number, or NaN)

    Returns:
        Lowercase, stripped string for comparison
    """
    if pd.isna(value) or value == '':
        return ''
    return str(value).strip().lower()


def normalize_well_format(well: str, default_rack: int = 1) -> str:
    """
    Add rack suffix to well position if not present and uppercase letter part.

    Examples:
        a1 → A1.1
        b2.3 → B2.3
        A1 → A1.1
    """
    if pd.isna(well) or not str(well).strip():
        return ''

    well = str(well).strip().upper()
    return well if '.' in well else f"{well}.{default_rack}"


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure dataframe has all required columns in the correct order.

    Adds any missing columns from ALL_COLUMNS (filled with None).
    Reorders columns to match ALL_COLUMNS.
    Strips leading/trailing whitespace from string fields.
    Normalizes well format for location fields (uppercase, adds rack suffix).

    Args:
        df: Input dataframe (may have missing columns)

    Returns:
        Normalized dataframe with all columns in correct order
    """
    from .config import (
        ALL_COLUMNS,
        DNA_PART_NAME,
        CIRCUIT_NAME,
        TRANSFECTION_GROUP,
        DNA_ORIGIN,
        DNA_DESTINATION,
        TRANSFECTION_DESTINATION,
        PLATE_DESTINATION,
        CONCENTRATION,
        QUANTITY_DNA,
    )

    # Add missing columns with None values
    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Strip whitespace from key string fields
    string_fields = [DNA_PART_NAME, CIRCUIT_NAME, TRANSFECTION_GROUP]
    for col in string_fields:
        if col in df.columns:
            # fillna first to avoid 'nan' string, then convert to string and strip
            df[col] = df[col].fillna('').astype(str).str.strip()

    # Normalize well format for location fields (uppercase + add rack suffix)
    location_fields = [DNA_ORIGIN, DNA_DESTINATION, TRANSFECTION_DESTINATION, PLATE_DESTINATION]
    for col in location_fields:
        if col in df.columns:
            df[col] = df[col].apply(normalize_well_format)

    # Convert numeric columns to proper types (handles strings from AG Grid)
    numeric_fields = [CONCENTRATION, QUANTITY_DNA]
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Reorder columns to match ALL_COLUMNS (and only keep those columns)
    return df[ALL_COLUMNS]


@contextmanager
def normalized_groupby(df: pd.DataFrame, by: Union[str, List[str]], **kwargs):
    """
    Context manager for groupby with case-insensitive, whitespace-insensitive comparison.

    Creates temporary normalized columns, yields a GroupBy object, then cleans up
    the temporary columns automatically.

    Args:
        df: DataFrame to group
        by: Column name(s) to group by (string or list of strings)
        **kwargs: Additional arguments passed to groupby()

    Yields:
        DataFrameGroupBy object using normalized comparison keys

    Example:
        >>> with normalized_groupby(df, [CIRCUIT_NAME, TRANSFECTION_GROUP]) as grouped:
        ...     counts = grouped.size()
        # Temporary columns are automatically removed here
    """
    # Ensure 'by' is a list
    columns = [by] if isinstance(by, str) else list(by)

    # Create normalized column names
    temp_cols = [f'_norm_{col}' for col in columns]

    # Add normalized columns to the dataframe
    for col, temp_col in zip(columns, temp_cols):
        if col in df.columns:
            df[temp_col] = df[col].apply(normalize_for_comparison)

    try:
        # Yield the groupby object using the normalized columns
        yield df.groupby(temp_cols, **kwargs)
    finally:
        # Clean up temporary columns (use errors='ignore' in case they don't exist)
        df.drop(columns=temp_cols, inplace=True, errors='ignore')
