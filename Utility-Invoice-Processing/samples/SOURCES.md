# Sample provenance

Every PDF here was **downloaded from a real public URL** — none were generated or edited.
Utilities and regulators publish sample/specimen bills ("Musterrechnung", "factura ejemplo",
"understanding your bill") with realistic figures; one file is a genuine production invoice
that the billed business published itself. Verified 2026-07-25 (`file` magic, `pdftotext`).

## Main set (`samples/`)

| File | Vendor | Lang | Utility | Why it's in the set | Source |
|---|---|---|---|---|---|
| `exodo-es-electricity-es.pdf` | Iberdrola Clientes S.A.U. | es | electricity | **Genuine production invoice** (published by the billed company, Exodo Rental S.L. — business data only). DD/MM/YYYY, comma decimals. | [exodorental.com](https://exodorental.com/wp-content/uploads/2018/07/044359836820180613211631380002.pdf) |
| `vialis-fr-electricity-fr.pdf` | Vialis Énergies (Colmar) | fr | electricity | Real figures in text; `48 469 kWh` space-thousands; TOU sub-period + restated-total traps. | [energies.vialis.net](https://energies.vialis.net/sites/default/files/domain_vialis_energies/pdf/zoom-facture%20elec-HTA.pdf) |
| `weenergies-us-electric-gas-en.pdf` | We Energies | en | gas + electricity | Combined dual-commodity bill; cleanest therms sample; explicit `Bill Period: X to Y`. | [we-energies.com](https://www.we-energies.com/payment-bill/pdf/we-energies-sample-bill.pdf) |
| `sfpuc-us-water-en.pdf` | San Francisco PUC | en | water + sewer | Water billed in "units" (CCF) with a gallons conversion — real unit normalization work. | [sfpuc.gov](https://www.sfpuc.gov/sites/default/files/accounts-and-services/WaterSewerBillGuide_JUL23.pdf) |
| `swm-de-electricity-de.pdf` | Stadtwerke München | de | electricity | DD.MM.YYYY dates, dot-thousands (`7.140`), German labels (Verbrauchsstelle). | [swm.de](https://www.swm.de/dam/doc/kundenservice/rechnung/musterrechnung-strom.pdf) |
| `centralhudson-us-electric-en.pdf` | Central Hudson G&E | en | electricity | Canonical US layout, labelled billing period, month-name dates — the easy baseline. | [cenhud.com](https://www.cenhud.com/globalassets/pdf/esco-portal/sample-bill.pdf) |
| `midamerican-us-electric-en.pdf` | MidAmerican Energy | en | electricity + gas | Dual fuel (kWh **and** therms); billing period must be derived from two meter-read dates. | [midamericanenergy.com](https://www.midamericanenergy.com/media/pdf/samplebill.pdf) |
| `edf-fr-electricity-fr.pdf` | EDF Entreprises | fr | electricity | **Image-only bill body** — the text layer has annotations but no figures. Exercises the vision fallback; in text mode the correct output is `not_found`, not a hallucination. | [edf.fr](https://www.edf.fr/sites/entreprise/files/2024-04/facture_elec_om_sup36_kva.pdf) |

## Deliberate edge cases (`samples/edge_cases/`)

| File | Trap | Source |
|---|---|---|
| `cub-comed-us-electric-es.pdf` | Spanish-language US bill where **all dates are `00/00/0000` placeholders** — dates must come back null, never invented. | [citizensutilityboard.org](https://www.citizensutilityboard.org/espanol/wp-content/uploads/sites/2/2025/02/Making-Sense-of-Your-Electric-Bill-SPA.pdf) |
| `ppl-us-electric-en.pdf` | Year-less billing period ("May 2 - Jun 3") — year must be inferred or flagged. | [pplelectric.com](https://www.pplelectric.com/-/media/PPLElectric/At-Your-Service/Docs/General-Supplier-Reference-Information/Two-Bill-Example.pdf) |
| `lapalma-es-electricity-es.pdf` | Internally contradictory period (`31/05/2024` → `22/06/2021`) in a training deck — should surface as a validation flag, not silent acceptance. | [club.lapalmarenovable.es](https://club.lapalmarenovable.es/wp-content/uploads/2024/12/01-Pildora-Formativa-Factura-Luz-Nivel-Basico.pdf) |
