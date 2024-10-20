from unittest.mock import patch
from src.data_ingestion.sam_gov_ingestion import fetch_sam_gov_opportunities

# Mocking the SAM.gov API response
mock_sam_gov_response = {
    "opportunitiesData": [
        {
            "postedDate": "2023-12-30",
            "type": "Award Notice",
            "officeAddress": {"countryCode": "USA"},
        }
    ]
}


@patch("os.getenv", return_value="fake_api_key")  # Mock the SAM_GOV_API_KEY
@patch(
    "src.data_ingestion.sam_gov_ingestion.requests.get"
)  # Mock the requests.get call
def test_fetch_sam_gov_opportunities(mock_get, mock_getenv):
    # Mock the behavior of requests.get to return a fake response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_sam_gov_response

    posted_from = "01/01/2023"
    posted_to = "12/31/2023"
    df = fetch_sam_gov_opportunities(posted_from, posted_to)

    assert df is not None
    assert len(df) > 0
    assert df.iloc[0]["document_date"] == "2023-12-30"
