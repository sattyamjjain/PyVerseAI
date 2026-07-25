# Extraction accuracy report

Predictions: `invoices.csv` · scored fields: 7 per row

| Field | N | Exact | Norm. | Missing ✓ | Missing ✗ | Halluc. | Wrong | Accuracy |
|---|---|---|---|---|---|---|---|---|
| vendor_name | 11 | 3 | 8 | 0 | 0 | 0 | 0 | 100.0% |
| invoice_date | 11 | 9 | 0 | 2 | 0 | 0 | 0 | 100.0% |
| service_address | 11 | 0 | 9 | 1 | 0 | 1 | 0 | 90.9% |
| usage_amount | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| usage_unit | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| billing_period_start | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| billing_period_end | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| **overall** | 77 | 56 | 17 | 3 | 0 | 1 | 0 | **98.7%** |

## By language

| Language | Field judgments | Accuracy |
|---|---|---|
| de | 7 | 100.0% |
| en | 49 | 98.0% |
| es | 7 | 100.0% |
| fr | 14 | 100.0% |

_Labeled but not part of this run: `ppl-us-electric-en.pdf`_

## Provider comparison

| CSV | Overall accuracy |
|---|---|
| `invoices.csv` | 98.7% |
| `invoices.openai.csv` | 84.4% |
