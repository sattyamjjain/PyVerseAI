# Extraction accuracy report

Predictions: `invoices_edge.csv` · scored fields: 7 per row

| Field | N | Exact | Norm. | Missing ✓ | Missing ✗ | Halluc. | Wrong | Accuracy |
|---|---|---|---|---|---|---|---|---|
| vendor_name | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 100.0% |
| invoice_date | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 100.0% |
| service_address | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 100.0% |
| usage_amount | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| usage_unit | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| billing_period_start | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| billing_period_end | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| **overall** | 7 | 4 | 2 | 1 | 0 | 0 | 0 | **100.0%** |

## By language

| Language | Field judgments | Accuracy |
|---|---|---|
| en | 7 | 100.0% |

_Labeled but not part of this run: `centralhudson-us-electric-en.pdf`, `edf-fr-electricity-fr.pdf`, `exodo-es-electricity-es.pdf`, `midamerican-us-electric-en.pdf`, `sfpuc-us-water-en.pdf`, `swm-de-electricity-de.pdf`, `vialis-fr-electricity-fr.pdf`, `weenergies-us-electric-gas-en.pdf`_
