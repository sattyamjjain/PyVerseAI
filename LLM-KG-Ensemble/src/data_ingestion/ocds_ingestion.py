import pandas as pd
import os


# ocds_ingestion.py
def fetch_ocds_data():
    # Fetch OCDS data (mock example)
    data = {
        "ocds_date": ["2023-10-01", "2023-10-10"],
        "ocds_type": ["Contract", "Tender"],
        "region": ["India", "USA"],
    }
    df = pd.DataFrame(data)

    # Rename the columns to match the expected format
    df.rename(
        columns={
            "ocds_date": "document_date",
            "ocds_type": "document_type",
            "region": "country",
        },
        inplace=True,
    )

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/ocds_data.csv", index=False)
    print("OCDS data fetched and saved.")
