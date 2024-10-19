import requests
import pandas as pd


def fetch_world_bank_documents():
    url = "https://search.worldbank.org/api/v3/wds"
    params = {
        "format": "json",
        "qterm": "energy",
        "fl": "docdt,docty,count",
        "rows": 50,
        "os": 0
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'documents' in data and data['documents']:
            documents = []
            for key, doc in data['documents'].items():
                documents.append({
                    'document_date': doc.get('docdt'),
                    'document_type': doc.get('docty'),
                    'country': doc.get('count')
                })
            return pd.DataFrame(documents)
        else:
            print("No documents found in the API response.")
            return None
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None


if __name__ == "__main__":
    df = fetch_world_bank_documents()
    print(df.head())
    if df is not None:
        df.to_csv("data/processed/world_bank_documents.csv", index=False)
        print("Data saved to world_bank_documents.csv")
    else:
        print("No data to save.")
