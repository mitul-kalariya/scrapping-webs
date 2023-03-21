""" General functions """
from datetime import timedelta, datetime
import json
import os

from scrapy.loader import ItemLoader

# from scrapy import log
from newton_scrapping.items import (
    IndianNewsArticleRawResponse,
    IndianNewsArticleRawParsedJson,
)

ERROR_MESSAGES = {
    "MISSING_REQUIRED_FIELD": "'{}' field is required.",
    "VALID_DATE_RANGE": "Please provide valid date range.",
    "BETWEEN_DATE_RANGE": "Please provide date range between 30 days",
    "NOT_REQUIRED_FIELD": "Invalid argument. {}",
}


def sitemap_validations(
    scrape_start_date: datetime, scrape_end_date: datetime, article_url: str
) -> datetime:
    """
    Validate the sitemap arguments

    Args:
        scrape_start_date (datetime): scrapping start date
        scrape_end_date (datetime): scrapping end date
        article_url (str): article url
    Returns:
        date: return current date if user not passed any date parameter
    """
    current_date = None
    if scrape_start_date and scrape_end_date:
        validate_arg("VALID_DATE_RANGE", not scrape_start_date > scrape_end_date)
        validate_arg(
            "BETWEEN_DATE_RANGE",
            int((scrape_end_date - scrape_start_date).days) <= 30,
        )
    else:
        validate_arg(
            "MISSING_REQUIRED_FIELD",
            not (scrape_start_date or scrape_end_date),
            "start_date and end_date",
        )
        current_date = datetime.now().date()

    validate_arg(
        "NOT_REQUIRED_FIELD", not article_url, "url is not required for sitemap."
    )

    return current_date


def article_validations(
    article_url: str, scrape_start_date: datetime, scrape_end_date: datetime
) -> None:
    """
    Validate the article arguments

    Args:
        article_url (str): article url
        scrape_start_date (datetime): scrapping start date
        scrape_end_date (datetime): scrapping end date
    Returns:
        None
    """

    validate_arg("MISSING_REQUIRED_FIELD", article_url, "url")
    validate_arg(
        "NOT_REQUIRED_FIELD",
        not (scrape_start_date or scrape_end_date),
        "start_date and end_date argument is not required for article.",
    )


def date_range(start_date: datetime, end_date: datetime) -> iter:
    """
    Return range of all date between given date
    if not end_date then take start_date as end date

    Args:
        scrape_start_date (datetime): scrapping start date
        scrape_end_date (datetime): scrapping end date
    Returns:
        iter: range of all date between given date
    """
    for date in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(date)


def validate_arg(param_name, param_value, custom_msg=None):
    """
    Validate the param.

    Args:
        param_name: Name of the parameter to be validated
        param_value: Value of the required parameter

    Raises:
        ValueError if not provided
    Returns:
          Value of parameter
    """
    if not param_value:
        raise ValueError(ERROR_MESSAGES[param_name].format(custom_msg or param_name))


def based_on_scrape_type(scrape_type, scrape_start_date, scrape_end_date, url):
    """check scrape type and based on scrape type pass to the vaildation function,
    after validation return required values."""
    if scrape_type == "article":
        article_validations(url, scrape_start_date, scrape_end_date)
        return None, None
    if scrape_type == "sitemap":
        scrape_start_date = scrape_end_date = sitemap_validations(
            scrape_start_date, scrape_end_date, url
        )
        date_range_lst = []
        date_range_lst.extend(iter(date_range(scrape_start_date, scrape_end_date)))
        return scrape_start_date, date_range_lst

    return validate_arg("MISSING_REQUIRED_FIELD", None, "type")


def raw_response_data(response, selector_and_key):
    """Raw response data generated from given response and selctor"""
    indian_news_article_raw_response_loader = ItemLoader(
        item=IndianNewsArticleRawResponse(), response=response
    )
    for key, value in selector_and_key.items():
        indian_news_article_raw_response_loader.add_value(key, value)
    return dict(indian_news_article_raw_response_loader.load_item())


def parsed_json(response, selector_and_key):
    """Parsed json response data generated from given response and selctor"""
    indian_news_article_raw_parsed_json_loader = ItemLoader(
        item=IndianNewsArticleRawParsedJson(), response=response
    )

    for key, value in selector_and_key.items():
        indian_news_article_raw_parsed_json_loader.add_value(
            key, [json.loads(data) for data in value.getall()]
        )
    return dict(indian_news_article_raw_parsed_json_loader.load_item())


def export_data_to_json_file(scrape_type, file_data, file_name):
    """Export data to json file"""
    folder_structure = ""
    if scrape_type == "sitemap":
        folder_structure = "Links"
        filename = (
            f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )

    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)

    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)
