import requests
import pandas as pd
import os


def fetch_sam_gov_opportunities(posted_from, posted_to):
    url = "https://api.sam.gov/opportunities/v2/search"
    api_key = os.getenv("SAM_GOV_API_KEY")
    params = {
        "api_key": api_key,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "rows": 50
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        opportunities = data.get('opportunitiesData', [])

        if opportunities:
            documents = []
            for opportunity in opportunities:
                documents.append({
                    'document_date': opportunity.get('postedDate'),
                    'document_type': opportunity.get('type'),
                    'country': opportunity.get('officeAddress', {}).get('countryCode', 'Unknown')
                })
            return pd.DataFrame(documents)
        else:
            print("No opportunities found in the API response.")
            return None
    else:
        print(f"Failed to fetch SAM.gov data. Status code: {response.status_code}")
        return None
