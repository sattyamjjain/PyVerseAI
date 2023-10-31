
# Verilog Hierarchy Analyzer

## Overview

Verilog Hierarchy Analyzer is a Python tool designed to parse Verilog netlists, extract module hierarchies, and count instances of modules and primitives in the design. It provides insight into the composition of Verilog designs, aiding in understanding, debugging, and documenting digital circuits.

## Features

- **Module Hierarchy Extraction**: Extracts the hierarchy of modules and their instances from a Verilog netlist.
- **Primitive and Module Instance Counting**: Counts the number of instances of each primitive and module in the specified hierarchy.
- **Support for Various Primitives**: Recognizes and counts various Verilog primitives such as `invN1`, `nand2N1`, and `nor2N1`.

## Requirements

- Python 3.x

## Installation

**Clone the Repository**: Clone this repository to your local machine.
    ```sh
    git clone https://github.com/sattyamjjain/PyVerseAI.git
    cd Verilog-Hierarchy-Analyzer
    ```

## Usage

1. **Prepare the Verilog File**: Ensure that your Verilog netlist file is ready and accessible.

2. **Run the Analyzer**:
    ```sh
    python3 main.py
    ```
3. **View Results**: The script will output the number of instances for each module and primitive in the specified hierarchy.

## Example

Input Verilog File (`example.v`):
```verilog
module TopCell(input [7:0] data, output out1, out2);
    // Your Verilog code here
endmodule
```

Output:
```
nand2N1         : 1 placements
nor2N1          : 2 placements
invN1           : 10 placements
bufferCell      : 4 placements
```

## Contributing

Contributions to improve Verilog Hierarchy Analyzer are welcome. Feel free to open issues or submit pull requests.
