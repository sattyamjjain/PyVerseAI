# Generate Repayment Schedule Program - Comprehensive Test Report

## Introduction

This comprehensive report outlines the different test cases, expected outcomes, and results for the repayment schedule generation program. The program is designed to calculate monthly interest payments and generate a complete schedule for loan repayment.

## Test Environment Setup

- Function Under Test: generate_repayment_schedule
- Parameters:
  - `principal (float)`: The principal loan amount.
  - `irpa (float): `Interest rate per annum.
  - `start_date (str)`: The start date of the loan in 'YYYY-MM-DD' format.
  - `part_payment_date (str, optional)`: The date of part payment in 'YYYY-MM-DD' format.
  - `remaining_amount (float, optional)`: The remaining loan amount after part payment.
  
## Test Cases
  
### Test Case 1: Standard Loan Repayment (No Part Payment)
  
#### Scenario Description
Evaluate the repayment schedule generation for a standard loan without any part payments.

#### Input Parameters

**Principal:** 10,000 Rs

**Interest Rate:** 12%

**Start Date:** October 7, 2023

#### Expected Outcome
- Monthly interest payments should be accurately calculated based on the given principal amount and annual interest rate.
- The last payment in the schedule should include the entire remaining principal amount, marking the end of the loan repayment period.

#### How to Run

`python3 -m unittest -v tests.test_schedule_generation.TestScheduleGeneration.test_start_date_october_7`


### Test Case 2: Loan Repayment with Part Payment

#### Scenario Description

Evaluate the repayment schedule generation when a part payment is made, altering the remaining loan amount.

#### Input Parameters

**Principal:** 5,000 Rs

**Interest Rate:** 12%

**Start Date:** October 24, 2023

**Part Payment Date:** January 15, 2024

**Remaining Amount:** 2,500 Rs

#### Expected Outcome

- Monthly interest payments before the part payment date should be calculated based on the original principal amount.
- On the part payment date:
    - Interest for the days before the part payment should be calculated based on the original principal.
    - Interest for the days after the part payment should be calculated based on the remaining amount.
- Subsequent monthly payments should be calculated based on the new principal amount (2,500 Rs).
- The final payment should include the remaining principal amount.
    
#### How to Run

`python3 -m unittest -v tests.test_schedule_generation_with_part_repayment.TestScheduleGenerationWithPartPayment.test_start_date_october_24`

### Running the Tests and Generating Reports

1. Ensure Python and all necessary packages are installed in your environment.
2. Navigate to the directory containing the test file in your terminal.
3. Run the tests using the python -m unittest -v command to enable verbose mode, ensuring detailed output for each test case.

### Interpreting Test Results

- **PASS:** Indicates that the program's output matches the expected output for the given test case.
- **FAIL:** Indicates a discrepancy between the expected and actual outcomes. Detailed output will help identify the differences and facilitate debugging.