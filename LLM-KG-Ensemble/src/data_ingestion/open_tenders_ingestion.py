import os

import pandas as pd


def fetch_open_tenders():
    # Fetch open tenders data and save to CSV (mocked example)
    data = {
        "tender_date": ["2023-11-01", "2023-11-05"],
        "tender_type": ["Public", "Private"],
        "country": ["USA", "Canada"],
    }
    df = pd.DataFrame(data)

    # Rename columns to match expected format
    df.rename(
        columns={"tender_date": "document_date", "tender_type": "document_type"},
        inplace=True,
    )

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/open_tenders.csv", index=False)
    print("Open Tenders data fetched and saved.")
