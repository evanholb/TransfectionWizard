"""Convert between DataFrame and Biocompiler JSON format."""

import json5
import pandas as pd
import re
from typing import Optional

from .config import (
    CIRCUIT_NAME,
    TRANSFECTION_GROUP,
    TRANSFECTION_TYPE,
    DNA_PART_NAME,
    CONCENTRATION,
    QUANTITY_DNA,
    DNA_ORIGIN,
    DNA_DESTINATION,
    TRANSFECTION_DESTINATION,
    PLATE_DESTINATION,
    ERN_PARTS,
    MARKER_PARTS,
)


def parse_json(content: str) -> pd.DataFrame:
    """
    Parse biocompiler JSON/JSON5 format into DataFrame.

    Biocompiler format:
    {
        "name": "circuit_name",
        "description": "ng DNA = 650.0",
        "content": [
            {
                "sources": [
                    {"plasmid": "DNA_part", "ratio": 0.15}
                ]
            }
        ]
    }

    Or array of circuits: [{circuit1}, {circuit2}, ...]

    Args:
        content: JSON/JSON5 string

    Returns:
        DataFrame with experiment data

    Raises:
        ValueError: If JSON is invalid or missing required fields
    """
    try:
        data = json5.loads(content)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {str(e)}")

    # Handle both single circuit and array of circuits
    if isinstance(data, dict):
        circuits = [data]
    elif isinstance(data, list):
        circuits = data
    else:
        raise ValueError("JSON must be an object or array of objects")

    rows = []

    for circuit in circuits:
        # Validate required fields
        if 'name' not in circuit:
            raise ValueError("Circuit missing required 'name' field")
        if 'content' not in circuit:
            raise ValueError(f"Circuit '{circuit['name']}' missing required 'content' field")

        circuit_name = circuit['name']

        # Extract total DNA from description
        total_dna = None
        if 'description' in circuit:
            match = re.search(r'ng DNA\s*=\s*([\d.]+)', circuit['description'])
            if match:
                total_dna = float(match.group(1))

        # Generate group names
        num_groups = len(circuit['content'])
        if num_groups == 3:
            group_names = ['X1', 'X2', 'Bias']
        else:
            group_names = [f'X{i+1}' for i in range(num_groups)]

        # Process each transfection group
        for group_idx, group in enumerate(circuit['content']):
            if 'sources' not in group:
                raise ValueError(f"Circuit '{circuit_name}' group {group_idx} missing 'sources' field")

            group_name = group_names[group_idx]
            sources = group['sources']

            # Determine transfection type
            transfection_type = 'Co' if len(sources) > 1 else 'Single'

            # Process each DNA part (source)
            for source in sources:
                if 'plasmid' not in source:
                    raise ValueError(f"Source in circuit '{circuit_name}' group '{group_name}' missing 'plasmid' field")
                if 'ratio' not in source:
                    raise ValueError(f"Source in circuit '{circuit_name}' group '{group_name}' missing 'ratio' field")

                plasmid_name = source['plasmid']
                ratio = float(source['ratio'])

                # Calculate DNA amount if total DNA is known
                dna_amount = (ratio * total_dna) if total_dna else None

                row = {
                    CIRCUIT_NAME: circuit_name,
                    TRANSFECTION_GROUP: group_name,
                    TRANSFECTION_TYPE: transfection_type,
                    DNA_PART_NAME: plasmid_name,
                    CONCENTRATION: None,  # Not specified in biocompiler format
                    QUANTITY_DNA: dna_amount,
                    DNA_ORIGIN: None,
                    DNA_DESTINATION: None,
                    TRANSFECTION_DESTINATION: None,
                    PLATE_DESTINATION: None
                }
                rows.append(row)

    if not rows:
        raise ValueError("No data found in JSON")

    return pd.DataFrame(rows)


def convert_to_json(df: pd.DataFrame, circuit_name: Optional[str] = None) -> str:
    """
    Convert DataFrame to biocompiler JSON5 format.

    Args:
        df: DataFrame with experiment data
        circuit_name: Optional. If provided, export only this circuit as single object.
                     If None, export all circuits as array.

    Returns:
        JSON5 string (single circuit object or array of circuits)
    """
    if df.empty:
        return '[]'

    # Filter by circuit if specified
    if circuit_name:
        df = df[df[CIRCUIT_NAME] == circuit_name].copy()
        if df.empty:
            raise ValueError(f"Circuit '{circuit_name}' not found in data")

    circuits = []

    # Group by circuit
    for circuit, circuit_df in df.groupby(CIRCUIT_NAME, sort=False):
        # Calculate total DNA for this circuit
        total_dna = circuit_df[QUANTITY_DNA].sum()

        # Get transfection groups
        groups = []
        group_names = circuit_df[TRANSFECTION_GROUP].unique().tolist()

        # Sort groups to maintain order (X1, X2, Bias or X1, X2, X3...)
        def sort_key(name):
            # Handle Bias specially
            if name == 'Bias':
                return (999, name)
            # Extract number from X1, X2, etc.
            match = re.match(r'X(\d+)', str(name))
            if match:
                return (int(match.group(1)), name)
            return (1000, name)

        group_names.sort(key=sort_key)

        for group_name in group_names:
            group_df = circuit_df[circuit_df[TRANSFECTION_GROUP] == group_name]

            sources = []
            for _, row in group_df.iterrows():
                dna_amount = row[QUANTITY_DNA]
                ratio = dna_amount / total_dna if total_dna > 0 else 0

                sources.append({
                    'plasmid': row[DNA_PART_NAME],
                    'ratio': ratio
                })

            groups.append({'sources': sources})

        circuit_obj = {
            'name': str(circuit),
            'description': f'ng DNA = {total_dna}',
            'content': groups
        }
        circuits.append(circuit_obj)

    # Return single object or array depending on input
    if circuit_name:
        # Single circuit - return as object
        return json5.dumps(circuits[0], indent=3)
    else:
        # Multiple circuits - return as array
        return json5.dumps(circuits, indent=3)


# ERN_PARTS and MARKER_PARTS are imported from config


def parse_output_name(dna_part_name: str) -> tuple:
    """
    Parse output DNA part name into receptor and fluorescent protein components.

    Output names follow the pattern: <receptor>_rec_<fluorescent>
    e.g., 'PgU_rec_mNeonGreen' -> ('PgU_rec', 'mNeonGreen')

    Args:
        dna_part_name: Name like 'PgU_rec_mNeonGreen' or 'CasE_rec_mKO2'

    Returns:
        Tuple of (receptor_part, fluorescent_part)
    """
    name = str(dna_part_name).strip()

    # Find the position of '_rec_' to split
    rec_idx = name.find('_rec_')
    if rec_idx != -1:
        receptor = name[:rec_idx + 4]  # Include '_rec'
        fluorescent = name[rec_idx + 5:]  # After '_rec_'
        return (receptor, fluorescent)

    # Fallback: if no fluorescent part found, return the whole name
    return (name, None)


def get_unit_type(dna_part_name: str) -> Optional[str]:
    """
    Determine unit type from DNA part name.

    Args:
        dna_part_name: Name of the DNA part

    Returns:
        'marker', 'ern', 'output', or None if unknown
    """
    if pd.isna(dna_part_name):
        return None

    name = str(dna_part_name).strip()

    # Check for output first (contains rec_)
    if 'rec_' in name:
        return 'output'

    # Check for ERN
    if name in ERN_PARTS:
        return 'ern'

    # Check for marker (fluorescent protein)
    if name in MARKER_PARTS:
        return 'marker'

    return None


def convert_to_biocompiler_recipe(df: pd.DataFrame, circuit_name: str) -> dict:
    """
    Convert circuit data to biocompiler API recipe format.

    Args:
        df: DataFrame with experiment data
        circuit_name: Name of the circuit to convert

    Returns:
        Recipe dict in biocompiler API format

    Raises:
        ValueError: If circuit not found, missing X1/X2 groups, or missing markers
    """
    circuit_df = df[df[CIRCUIT_NAME] == circuit_name].copy()
    if circuit_df.empty:
        raise ValueError(f"Circuit '{circuit_name}' not found")

    groups = circuit_df[TRANSFECTION_GROUP].unique().tolist()

    # Validate X1 and X2 exist
    if 'X1' not in groups or 'X2' not in groups:
        raise ValueError("Circuit must have X1 and X2 transfection groups for prediction")

    # Build input_order from markers in X1 and X2
    input_order = []
    for group in ['X1', 'X2']:
        group_df = circuit_df[circuit_df[TRANSFECTION_GROUP] == group]
        marker_found = False
        for _, row in group_df.iterrows():
            if get_unit_type(row[DNA_PART_NAME]) == 'marker':
                input_order.append(row[DNA_PART_NAME])
                marker_found = True
                break
        if not marker_found:
            raise ValueError(f"Group {group} must have a marker (fluorescent protein)") ###############

    # Sort groups for consistent ordering (X1, X2, X3, ..., Bias)
    def sort_key(name):
        if name == 'Bias':
            return (999, name)
        match = re.match(r'X(\d+)', str(name))
        if match:
            return (int(match.group(1)), name)
        return (1000, name)

    groups.sort(key=sort_key)

    # Build content array
    content = []
    for group_name in groups:
        group_df = circuit_df[circuit_df[TRANSFECTION_GROUP] == group_name]

        units = []
        ratios = []
        total_dna = group_df[QUANTITY_DNA].sum()

        for _, row in group_df.iterrows():
            unit_type = get_unit_type(row[DNA_PART_NAME])
            if unit_type is None:
                raise ValueError(f"Unknown DNA part type: {row[DNA_PART_NAME]}")

            unit_name = f"{group_name.lower()}_{unit_type}"

            # Build slots array based on unit type
            if unit_type == 'output':
                # Outputs have 4 slots: [promoter, receptor, fluorescent, terminator]
                receptor, fluorescent = parse_output_name(row[DNA_PART_NAME])
                if fluorescent is None:
                    raise ValueError(
                        f"Output '{row[DNA_PART_NAME]}' must include fluorescent protein "
                        f"(e.g., 'PgU_rec_mNeonGreen')"
                    )
                slots = ["hEF1a", receptor, fluorescent, "L0.T_4560"]
            else:
                # Markers and ERNs have 3 slots: [promoter, protein, terminator]
                slots = ["hEF1a", row[DNA_PART_NAME], "L0.T_4560"]

            unit = {
                "name": unit_name,
                "slots": slots
            }
            if unit_type == 'marker':
                unit["no_masking"] = True

            units.append(unit)
            ratio = row[QUANTITY_DNA] / total_dna if total_dna and total_dna > 0 else 0
            ratios.append(ratio)

        content.append({
            "name": group_name.lower(),
            "units": units,
            "ratios": ratios
        })

    return {
        "name": circuit_name,
        "input_order": input_order,
        "content": content
    }
