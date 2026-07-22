# TransfectionWizard

An app to streamline genetic circuit experiment design, configuration, and analysis

## Overview

TransfectionWizard streamlines the process of designing & configuring DNA genetic circuit experiments for execution with an Opentrons liquid handling robot. It automatically fills in incomplete plate layouts, validates experimental configuration, and produces downloadable plate layout guides and ready-to-upload Opentrons protocols. Experiments can be converted between human-readable tabular data (CSV) and Biocompiler format (JSON5). In the future, the external Biocompiler-Predict tool will enable in-app preview of predicted 2D heatmap-style genetic circuit designs.

### Key Features

- **Multiple Input Formats**: CSV, Biocompiler JSON/JSON5, Opentrons OT-2 Python scripts
- **Automatic Layout Generation**: Intelligent assignment of DNA parts, destinations, and output wells across input racks and output plates. Fills in all missing slots while respecting user-specified values to create a valid OT-2 experiment layout
- **Real-time Validation**: Immediate feedback on design constraints and errors
- **Interactive Table Editing**: Edit experiment parameters directly in the web interface
- **Visual Plate Layouts**: Color-coded visualization of all rack and plate layouts
- **Circuit Prediction Integration**: Export circuits to Biocompiler format and run prediction
- **Multi-Format Export**:
  - Excel file with color-coded plate layouts
  - CSV configuration file
  - Biocompiler JSON5 format
  - Opentrons Python protocol (ready to upload)

---

## Quick Start

### Installation

**First time setup:**

```bash
# 1. Download the app and cd into that folder
git clone https://github.com/evanholb/TransfectionWizard.git
cd TransfectionWizard

# 2. Create a new virtual environment with conda:
conda create -n fect_wiz python==3.10
conda activate fect_wiz

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests (optional)
pytest tests/ -v

# 5. Start the application
python3 main.py
```

App will be available in your browser at: `http://localhost:8080`


**Next time** (after first setup):

```bash
conda activate fect_wiz
python3 main.py
```

### Use TransfectionWizard 

**Step 1: Upload or Create Data**

Click **"Upload File"** and select your file, or click "Add Row" to start from scratch.

You can add data to an experiment from any of the following:
- A CSV file containing your experiment design
- An existing Opentrons .py script (extracts and validates embedded CSV)
- A Biocompiler JSON/JSON5 file (automatically converts to table format)
- Manual entry using the "Add Row" button

You can also upload a Opentrons .py script *template* (i.e. no embedded CSV -- see example in `data/OT2_automated_transfection_v3.9.py`) and it will be added to the list of available templates (automatically selected as the active template upon upload)

**Step 2: Edit & Automate**

1. Review/edit/add/delete data in the interactive table
2. Click **"Create Layout"** to automatically assign slots and validate
3. View the generated layouts in the visualization section

**Step 3: Simulate**

Run Opentrons Simulator and review the logs directly in the app.

**Step 4: Download Results**

- **All Files (.zip)** - Complete bundle with all outputs
- **Experiment Config (.csv)** - Full layout data
- **Plate Layouts (.xlsx)** - Visual Excel layouts
- **Biocompiler Format (.json5)** - Circuit format for prediction tools
- **Opentrons Protocol (.py)** - Robot-ready script

**Step 5: Predict (not implemented)**

Switch to the **Predict** tab to:
- Select a circuit from your design
- Display the 2D-heatmap image predicted by Biocompiler-Predict (currently just shows the json string that will be sent to the external tool)

---

## Input Format Details

You can provide your experiment data in different ways:

### Minimal Input (Recommended)

Provide just the essential experiment details (upload as a csv or as an OT-2 script .py file with csv embedded.) All slot assignments will be automatically generated.

| Column Name | Description | Example |
|------------|-------------|---------|
| Circuit name | Unique identifier for each circuit | C1, Circuit1 |
| Transfection group | Group within circuit | X1, X2, Bias |
| Contents | Name of the DNA part | mKO2, Csy4rec_mNG |
| Concentration (ng/uL) | DNA concentration | 50 |
| DNA wanted (ng) | Amount of DNA to add | 100 |

**Example CSV:**

```csv
Circuit name,Transfection group,Contents,Concentration (ng/uL),DNA wanted (ng)
MyCircuit,X1,Csy4rec_mNG,50,100
MyCircuit,X1,mKO2,50,100
MyCircuit,X2,Csy4,25,50
MyCircuit,X2,PacBlue,50,100
```

### Legacy Specification

Alternatively, specify exact slot positions (upload as a csv or as an OT-2 script .py file with csv embedded.) This is commonly the format for experiments that have already been run. Circuit names and groups will be automatically inferred from your slot assignments.

| Column Name | Description | Example |
|------------|-------------|---------|
| DNA source | Source slot for DNA part | A1.1 |
| DNA destination | Destination slot for DNA | B1.1 |
| L3K/OM MM destination | Transfection mix destination | C1.1 |
| Plate destination | Output well | A1.1 |
| Contents | Name of the DNA part | mNG |
| Concentration (ng/uL) | DNA concentration | 50 |
| DNA wanted (ng) | Amount of DNA to add | 100 |

### Biocompiler JSON Format

Import circuits directly from Biocompiler format (JSON/JSON5) files.

**Example JSON:**

```json
{
  "name": "MyCircuit",
  "description": "ng DNA = 650.0",
  "content": [
    {
      "sources": [
        {"plasmid": "Csy4rec_mNG", "ratio": 0.4},
        {"plasmid": "mKO2", "ratio": 0.1}
      ]
    },
    {
      "sources": [
        {"plasmid": "Csy4", "ratio": 0.25},
        {"plasmid": "PacBlue", "ratio": 0.25}
      ]
    }
  ]
}
```

The above example is for a single circuit, but an array of multiple circuits is also valid: `[{circuit1}, {circuit2}, ...]`

**Biocompiler Format Conversion:**
- Transfection groups are auto-named: X1, X2, Bias (for 3 groups) or X1, X2, X3, X4... (for more than 3 groups, i.e. not a 2D heatmap experiment)
- DNA quantities are calculated from ratios and total DNA
- Concentration must be added manually in the table (not included in Biocompiler format)

---

## Validation Rules

The application performs comprehensive validation before layout generation. Validation is organized into the following categories:

### 1. Required Field Errors
- All essential columns must be present and non-empty (either minimal format OR full format)
- Contents, Concentration, and DNA wanted are **always** required

### 2. Layout Compatibility Errors
- **96-well layouts only:** DNA sources must be in rack 1 (DNA parts are expected to be in tubes placed in the 24-tube rack, which is rack 1)
- **96-well layouts only:** DNA destinations, transfection destinations, and diluted sources must be in 96-well plates (racks 2-3)
- **24-tube layouts:** No distinction between input rack 1 vs 2-3 (all input racks are 24-tube racks)

### 3. Slot Conflict Errors
- Same slot cannot be assigned to distinct entities within or across different **input** racks
- Note that input slots names overlap with output slots as input and output plates are separately numbered

### 4. Grouping Rule Violations
- Same DNA part must always use the same source slot
- Same circuit + transfection group combo must always use the same DNA destination
- Same circuit + transfection group combo must always use the same L3K/OM MM destination
- Same circuit must always use the same plate destination

### 5. Circuit DNA Limit
- Total DNA per circuit (sum of all DNA wanted (ng) values for parts in the same circuit) cannot exceed 800 ng

### Common Validation Errors

If validation fails, you'll see clear error messages with specific row numbers and values:

- **Missing required fields** → Add the missing data
- **DNA exceeds 800ng** → Reduce DNA quantities
- **Duplicate/inconsistent slots** → Manually fix slot conflicts or press "reset layout" button to start fresh
- **Pool separation violation** → Move DNA sources to rack 1
- **Grouping inconsistency** → Ensure same parts/circuits use consistent slots

---

## Dilution Logic

The application automatically determines when DNA dilution is required and assigns dilution slots.

### When is Dilution Needed?

Dilution is required when the pipetting volume would be too small for accurate handling:

**Formula:** `DNA_wanted (ng) < MIN_PIPETTE_VOLUME (2 µL) × Concentration (ng/µL)`

**Example:**
- DNA wanted: 100 ng
- Concentration: 500 ng/µL
- Required volume: 100 ng ÷ 500 ng/µL = 0.2 µL ❌ Too small!
- **Dilution needed:** Yes, a diluted source will be automatically assigned

### How Dilution Works

1. **Automatic Detection:** During layout generation, the system checks if each DNA part needs dilution
2. **Slot Assignment:** Parts requiring dilution get a "Diluted source" slot assigned
3. **Shared Dilutions:** The same DNA part (same name) shares the same diluted source slot across all uses

### Dilution in Different Layouts

- **24-tube layout:** Diluted sources assigned from input racks (racks 1-2 required, rack 3 optional)
- **96-well layout:** Diluted sources assigned from racks 2-3 (well plates only, same pool as DNA destinations)

---

## Layout Types and Slot Notation

### Slot Notation Format

Slots are specified as `WellPosition.RackNumber`:
- `A1.1` = well A1 in rack 1
- `B3.2` = well B3 in rack 2
- `D6.3` = well D6 in rack 3

**Note:** Rack numbers are logical (1, 2, 3...) and represent the user-facing rack numbering. The mapping to physical OT-2 labware slot positions is handled internally by the application.

### Layout Selection

Layout type is determined by the currently selected template in the dropdown menu:
- Templates define whether you're using 24-tube racks or 96-well plates
- When you upload an Opentrons .py script, that template is automatically selected
- You can also manually select a different template from the dropdown

### 24-Tube Layout (v3.8/v3.9)

- **Input Racks 1-3:** All tube racks (24 positions each: A1-D6)
  - All racks required
  - All racks can hold DNA sources, DNA destinations, transfection destinations, and diluted sources
- **Output Plates 1-2:** 24-well plates (A1-D6)
  - Plate 1 required, plate 2 optional
- **Shared Pool:** DNA sources and destinations can be in any input rack (no separation required)
- **Total Capacity:** 72 input positions (66 available after reagent slots), 48 output wells
- **Reagent Slots:** D1.3, D2.3, D3.3, D4.3, D5.3, D6.3 (reserved in rack 3)

### 96-Well Layout (High-Throughput)

- **Rack 1:** Tube rack (24 positions: A1-D6)
  - Required
  - DNA sources ONLY
- **Racks 2-3:** 96-well plates (96 positions each: A1-H12)
  - Rack 2 required, rack 3 optional
  - DNA destinations, transfection destinations, and diluted sources ONLY
- **Output Plates 1-2:** 24-well plates (A1-D6)
  - Plate 1 required, plate 2 optional
- **Pool Separation Enforced:** DNA sources expected to be in rack 1, all destinations in racks 2-3
- **Total Capacity:** 18 DNA source positions (6 reagent slots reserved in rack 1), 192 destination positions, 48 output wells
- **Reagent Slots:** D1.1, D2.1, D3.1, D4.1, D5.1, D6.1 (reserved in rack 1)

---

## Plate Layout Color Legend

- **Green** = DNA sources (DNA input tubes)
- **Blue** = Destinations (working slots)
- **Pink** = Circuits (output wells)
- **Purple** = Reagents (reserved slots)
- **Gray** = Empty slots

---

## Troubleshooting

**App won't start?**
- Make sure you activated the environment `conda activate fect_wiz`
- Make sure you are in the correct directory where `main.py` exists (i.e. `TransfectionWizard/`)
- If it says the port is in use try killing the existing process: `lsof -ti:8080 | xargs kill -9`

**File upload fails?**
- Check the file extension: must be .csv, .py, .json, or .json5
- Check file encoding (should be UTF-8)
- Try the example files in `tests/example_input/`:
  - `minimal/` - Minimal format CSV examples (just circuit names and DNA parts)
  - `full/` - Full format CSV examples (explicit slot assignments)
  - `biocompiler/` - Biocompiler JSON/JSON5 examples
  - `opentrons/` - Opentrons Python script examples

---

## Project Structure

```
TransfectionWizard/
├── core/
│   ├── config.py          # Configuration and constants
│   ├── validation.py      # Input validation logic
│   ├── layout.py          # Layout generation algorithms
│   ├── exporters.py       # File export functions
│   ├── json_converter.py  # JSON/JSON5 conversion
│   ├── script_utils.py    # Python script parsing
│   ├── state.py           # Application state management
│   └── utils.py           # General utility functions
├── ui/
│   ├── tabs/
│   │   ├── build.py       # Main design interface
│   │   ├── predict.py     # Circuit prediction/export
│   │   ├── generate.py    # (Placeholder for future features)
│   │   └── analyze.py     # (Placeholder for future features)
│   └── components/
│       ├── upload.py      # File upload handling
│       ├── table.py       # Interactive data table
│       ├── layout_gen.py  # Layout generation button
│       ├── visualization.py  # Plate visualizations
│       ├── plate_renderer.py # Plate rendering logic
│       ├── download.py    # File downloads
│       ├── grid_manager.py  # AG Grid state management
│       └── simulation.py  # Opentrons simulation interface
├── data/                  # Template Opentrons scripts
├── static/                # Static web assets (CSS, JavaScript)
├── tests/
│   ├── example_input/       # Test data with examples for all input formats
│   │   ├── biocompiler/     # Biocompiler JSON/JSON5 examples
│   │   ├── full/            # Full format CSV examples
│   │   ├── minimal/         # Minimal format CSV examples
│   │   └── opentrons/       # Opentrons script examples
│   ├── unit/               # Unit tests for core functions
│   │   ├── test_validation_rules.py
│   │   ├── test_slot_assignment.py
│   │   ├── test_inference.py
│   │   └── test_dilution_logic.py
│   ├── integration/        # Integration tests for end-to-end workflows
│   │   ├── test_24tube_layouts.py
│   │   ├── test_96well_layouts.py
│   │   └── test_full_workflow.py
│   ├── regression/         # Regression tests for example files
│   │   └── test_example_files.py
│   ├── conftest.py         # Pytest fixtures and configuration
│   └── __init__.py
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## Testing

The project includes comprehensive test coverage across multiple categories:

### Test Categories

- **Unit Tests:** Test individual functions and validation rules in isolation
- **Integration Tests:** Test end-to-end workflows with both 24-tube and 96-well layouts
- **Regression Tests:** Validate all example input files to ensure they continue to work correctly

### Running Tests

**Run all tests:**
```bash
pytest tests/ -v
```

**Run specific test categories:**
```bash
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests only
pytest tests/regression/ -v    # Regression tests only
```

**Run specific test file:**
```bash
pytest tests/unit/test_validation_rules.py -v
pytest tests/integration/test_24tube_layouts.py -v
```

**Run with coverage report:**
```bash
pytest tests/ --cov=core --cov-report=html
```

All tests should pass before committing changes. The test suite validates:
- Validation logic for all error types
- Slot assignment algorithms for both layout types
- Dilution logic and detection
- Circuit/group inference from legacy formats
- Grouping rule enforcement
- All example input files in multiple formats

---

## Technologies

- **Backend**: Python 3.10
- **Web Framework**: [NiceGUI](https://nicegui.io/)
- **Data Processing**: pandas, openpyxl, json5
- **Robot Integration**: Opentrons Python API
- **Testing**: pytest

---

**Last Updated**: December 2025
