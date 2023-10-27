
# Adaptive Repayment Calculator

The Adaptive Repayment Calculator is a tool designed to assist users in calculating their loan repayment schedules, taking into account the possibility of part payments and changes in the remaining amount. It provides a clear and concise breakdown of interest payments and the total amount due over the course of the loan.

## Features

- Calculation of loan repayment schedules over a one-year period
- Support for part payments and adjustments in remaining loan amounts
- Clear breakdown of interest payments and total amount due
- Robust error handling and input validation

## Requirements

- Python 3.x
- See `requirements.txt` for a full list of dependencies

## Installation

To set up the development environment, run:

```bash
pip install -r requirements.txt
```

## Usage

Run the main script to start the application:

```bash
python main.py
```

You can also provide command-line arguments to specify the loan details:

```bash
python main.py <principal> <irpa> <start_date> [--part_payment_date] [--remaining_amount]
```

- `principal`: The principal loan amount
- `irpa`: The annual interest rate as a percentage
- `start_date`: The start date of the loan in 'YYYY-MM-DD' format
- `part_payment_date`: (Optional) The date of the part payment in 'YYYY-MM-DD' format
- `remaining_amount`: (Optional) The remaining loan amount after the part payment

## Running Tests

To run the tests, navigate to the root directory and run:

```bash
python -m unittest -v
```

## Contributing

Contributions are welcome! If you have suggestions or find a bug, please open an issue or create a pull request.
