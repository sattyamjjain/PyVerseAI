from typing import List
from urllib.parse import urlparse

import requests
import argparse
from bs4 import BeautifulSoup
from db import ProductRepo
from config import AMAZON_URL_TO_SCRAPE, FLIPKART_URL_TO_SCRAPE
from utils import get_logger

_logger = get_logger(__name__)


def initialize_soup(url: str) -> BeautifulSoup:
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "DNT": "1",
            "Connection": "close",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    return BeautifulSoup(response.content, "html.parser")


def _scrape_amazon() -> List[dict]:
    soup = initialize_soup(AMAZON_URL_TO_SCRAPE)
    _products = []
    for product_element in soup.find_all("div", class_="p13n-sc-uncoverable-faceout"):
        _products.append(
            {
                "product_id": urlparse(
                    product_element.find("a", class_="a-link-normal")["href"]
                ).path.split("/")[3],
                "product_name": product_element.find(
                    "div", class_="_cDEzb_p13n-sc-css-line-clamp-3_g3dy1"
                ).text.strip(),
                "image": product_element.find("img", class_="a-dynamic-image")[
                    "data-a-dynamic-image"
                ].split('"')[1],
                "rating": product_element.find("i", class_="a-icon-star-small")
                .find("span", class_="a-icon-alt")
                .text.strip(),
                "Price": product_element.find(
                    "span", class_="_cDEzb_p13n-sc-price_3mJ9Z"
                ).text.strip(),
            }
        )
    return _products


def _scrape_flipkart() -> List[dict]:
    soup = initialize_soup(FLIPKART_URL_TO_SCRAPE)
    _products = []
    for _ps in soup.find_all("div", class_="_13oc-S _1t9ceu"):
        for _p in _ps.find_all("div", {"data-id": True}):
            if _p:
                product_name_element = _p.find("a", class_="IRpwTa")
                image_element = _p.find("img", class_="_2r_T1I")
                price_element = _p.find("div", class_="_30jeq3")
                discount_element = _p.find("div", class_="_3Ay6Sb")

                _products.append(
                    {
                        "product_id": _p["data-id"],
                        "product_name": product_name_element.get("title")
                        if product_name_element
                        else None,
                        "image": image_element["src"]
                        if image_element and "src" in image_element.attrs
                        else None,
                        "price": price_element.text.strip() if price_element else None,
                        "discount": discount_element.text.strip()
                        if discount_element
                        else None,
                    }
                )
    return _products


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E-commerce Scraper Suite")
    parser.add_argument(
        "--website",
        type=str,
        choices=["amazon", "flipkart"],
        help="Choose the website to scrape: 'amazon' or 'flipkart'",
        default="flipkart",
    )
    args = parser.parse_args()
    products = []

    try:
        if args.website == "amazon":
            products = _scrape_amazon()
        elif args.website == "flipkart":
            products = _scrape_flipkart()
        else:
            raise NotImplementedError

        _pr = ProductRepo()
        for product in products:
            _pr.add_product(
                product_id=product["product_id"],
                product_name=product.get("product_name"),
                price=product.get("price"),
                image=product.get("image"),
                rating=product.get("rating"),
                discount=product.get("discount"),
            )
    except Exception as e:
        _logger.error(str(e))
