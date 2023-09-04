import json
import requests
from bs4 import BeautifulSoup
import utils
import config

logger = utils.get_logger(__name__)


def fetch_news_data(url):
    """
    Fetch news data from the Y-combinator and return a list of news items.

    Parameters:
    - url (str): The URL from which the news data is to be scraped.

    Returns:
    - list: A list of dictionaries, with each dictionary representing a news item.
    """
    data_list = []

    # Making a GET request to the provided URL
    response = requests.get(url)

    # Checking for successful response
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")

        # Extracting the main table based on its unique attributes
        table2 = soup.find(
            "table",
            {
                "border": "0",
                "cellpadding": "0",
                "cellspacing": "0",
                "style": None,
                "width": None,
            },
        )

        # Iterating through each row of the table to extract relevant data
        for row in table2.find_all("tr"):
            data = {
                "id": None,
                "title_url": None,
                "title": None,
                "site_text": None,
                "score": None,
                "user": None,
                "time": None,
            }

            # Extracting the ID attribute from the row, if present
            tr_id = row.get("id")
            if tr_id:
                data["id"] = tr_id

            # Extracting news title and its URL
            title_line_tag = row.find("span", class_="titleline")
            if title_line_tag:
                a_tag = title_line_tag.find("a")
                data["title_url"] = a_tag.attrs["href"]
                data["title"] = a_tag.text

                # Extracting the site text (e.g., domain name)
                if title_line_tag.find("span", class_="sitebit comhead"):
                    site_span = title_line_tag.find(
                        "span", class_="sitebit comhead"
                    ).find("span", class_="sitestr")
                    data["site_text"] = site_span.text

            # Extracting additional details like score, user, and time
            elif row.find("span", class_="subline"):
                sub_line_tag = row.find("span", class_="subline")
                score_tag = sub_line_tag.find("span", class_="score")
                if score_tag and "id" in score_tag.attrs:
                    # Matching the news item's ID to append additional details
                    for _data in data_list:
                        if _data["id"] in score_tag["id"]:
                            data = {
                                **_data,
                                "score": score_tag.text,
                                "user": sub_line_tag.find("a").text,
                                "time": sub_line_tag.find("span", class_="age")
                                .find("a")
                                .text,
                            }
                            break
            else:
                continue

            # Removing older entries with the same ID
            for index, _data in enumerate(data_list):
                if _data["id"] == data["id"]:
                    data_list.pop(index)
                    break

            # Appending the extracted data to the results list
            data_list.append(data)
    else:
        # Logging an error in case of unsuccessful response
        logger.error(f"Failed to fetch data. HTTP Status Code: {response.status_code}")

    return data_list


if __name__ == "__main__":
    # Fetching the news data and storing it in a JSON file
    news = fetch_news_data(config.WEB_URL)

    with open("scrape_news.json", "w") as outfile:
        outfile.write(json.dumps(news, indent=4))
    logger.info("Data written to scrape_news.json")
