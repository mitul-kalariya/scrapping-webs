import json
import os
from datetime import datetime
from scrapy.http import Response
from scrapy.loader import ItemLoader

from newton_scrapping.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from newton_scrapping.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)

def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (ZeitDeNews): The ZeitDeNews spider instance.
        start_date (str): The start date for the sitemap spider in the format YYYY-MM-DD.
        end_date (str): The end date for the sitemap spider in the format YYYY-MM-DD.

    Raises:
        ValueError: If the type is not "articles" or "sitemap".
        ValueError: If the type is "sitemap" and either start_date or end_date is missing.
        ValueError: If the type is "sitemap" and the time range is more than 30 days.
        ValueError: If the type is "articles" and the URL is missing.

    Returns:
        None.

       Note:
           This function assumes that the class instance variable `start_urls` is already initialized as an empty list.
       """
    initial_url = "https://economictimes.indiatimes.com/etstatic/sitemaps/et/sitemap-index.xml"
    if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("Enter start_date and end_date for maximum 30 days.")
        else:
            self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
        today_time = datetime.today().strftime("%Y-%m-%d")
        self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
        self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:
        raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

    elif self.type == "article" and self.url is not None:
        self.start_urls.append(self.url)

    elif self.type == "article" and self.url is None:
        raise ValueError("type articles must be used with url")

    else:
        raise ValueError("type should be articles or sitemap")


def get_raw_response(response: str, selector_and_key: dict) -> dict:
    """
    Raw response data generated from given response and selector

    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector

    Returns:
        Dictionary with generated raw response
    """
    article_raw_response_loader = ItemLoader(
        item=ArticleRawResponse(), response=response
    )
    for key, value in selector_and_key.items():
        article_raw_response_loader.add_value(key, value)
    return dict(article_raw_response_loader.load_item())


def get_parsed_json(response: str, selector_and_key: dict) -> dict:
    """
     Parsed json response from generated data using given response and selector

    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector

    Returns:
        Dictionary with Parsed json response from generated data
    """

    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in selector_and_key.items():

        if key == "main":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if "NewsArticle" in json.loads(data).get('@type')]
            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "VideoObject"]
            )

        elif key == "VideoObject":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "VideoObject"]
            )
        else:
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "VideoObject" or json.loads(data).get('@type') != "NewsArticle"]
            )
    return dict(article_raw_parsed_json_loader.load_item())


def get_parsed_data_dict() -> dict:
    """
    Return base data dictionary

    Args:
    None

    Returns:
        dict: Return base data dictionary
    """
    return {
        "country": None,
        "language": None,
        "author": [{"@type": None, "name": None, "url": None}],
        "description": None,
        "modified_at": None,
        "published_at": None,
        "publisher": None,
        "text": None,
        "thumbnail_image": None,
        "title": None,
        "images": None,
        "section": None,
        "video": None,
    }

def get_parsed_data(response: str, parsed_json_dict: dict) -> dict:
    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in parsed_json_dict.items():
        article_raw_parsed_json_loader.add_value(
            key, [json.loads(data) for data in value.getall()]
        )
    parsed_data_dict = get_parsed_data_dict()
    article_data = dict(article_raw_parsed_json_loader.load_item())
    mapper = {"en": "English"}
    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict["source_country"] = ["India"]
    parsed_data_dict["source_language"] = [mapper.get(response.css("html::attr(lang)").get())]
    parsed_data_dict["author"] = [article_data.get("main")[1].get('author')]
    parsed_data_dict["description"] = [article_data.get("main")[1].get('description')]
    parsed_data_dict["modified_at"] = [article_data.get("main")[1]['dateModified']]
    parsed_data_dict["published_at"] = [article_data.get("main")[1]['datePublished']]
    # "retrieved_at": [datetime.today().strftime("%Y-%m-%d")],
    parsed_data_dict["publisher"] = [{'@type': article_data.get("main")[1].get('publisher').get('@type'),
        'name': article_data.get("main")[1].get('publisher').get('name'),
        'logo':{
            "@type": article_data.get("main")[1].get('publisher').get('logo').get('@type'),
            "url":article_data.get("main")[1].get('publisher').get('logo').get('url'),
            'width': {'@type': "Distance",
                "name": str(article_data.get("main")[1]['publisher']['logo']['width']) + " Px"},
            'height': {'@type': "Distance",
                'name': str(
                    article_data.get("main")[1]['publisher']['logo']['height']) + " Px"}}    
            }
    ]
    parsed_data_dict["text"] = [article_data.get("main")[1].get("articleBody")]
    parsed_data_dict["thumbnail_image"] = [article_data.get("img_url")]
    parsed_data_dict["title"] = article_data.get('main')[1].get('headline')
    parsed_data_dict["images"] = [{"link": article_data.get("main")[1].get('image').get('url')}]
    parsed_data_dict["section"] = [article_data.get('main')[1].get('articleSection')]
    parsed_data_dict["tags"] = article_data.get('main')[1].get('keywords')

    return remove_empty_elements(parsed_data_dict)


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param parsed_data_dict: Input dictionary.
    :type parsed_data_dict: dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
    :rtype: dict
    """

    def empty(value):
        return value is None or value == {} or value == []

    if not isinstance(parsed_data_dict, (dict, list)):
        data_dict = parsed_data_dict
    elif isinstance(parsed_data_dict, list):
        data_dict = [
            value
            for value in (remove_empty_elements(value) for value in parsed_data_dict)
            if not empty(value)
        ]
    else:
        data_dict = {
            key: value
            for key, value in (
                (key, remove_empty_elements(value))
                for key, value in parsed_data_dict.items()
            )
            if not empty(value)
        }
    return data_dict


def export_data_to_json_file(scrape_type: str, file_data: str, file_name: str) -> None:
    """
    Export data to json file

    Args:
        scrape_type: Name of the scrape type
        file_data: file data
        file_name: Name of the file which contain data

    Raises:
        ValueError if not provided

    Returns:
        Values of parameters
    """
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

    with open(f"{folder_structure}/{filename}", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)

