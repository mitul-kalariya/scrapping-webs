"""Utility Functions"""
import json
from datetime import datetime
from scrapy.loader import ItemLoader

from crwlinternaute.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)

from crwlinternaute.constant import SITEMAP_URL
from crwlinternaute.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)


def check_cmd_args(self, start_date: str, end_date: str) -> None:  # noqa: C901
    """
    Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (TimesNow): The TimesNow spider instance.
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

    def add_start_url(url):
        self.start_urls.append(url)

    def set_date_range(start_date, end_date):
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')

    def validate_date_range():
        if self.start_date > self.end_date:
            raise InvalidDateException("start_date must be less then end_date")
        if (self.end_date - self.start_date).days > 30:
            raise InvalidDateException("Enter start_date and end_date for maximum 30 days.")

    def validate_type():
        if self.type not in ["article", "sitemap"]:
            raise InvalidArgumentException("type should be articles or sitemap")

    def handle_sitemap_type():
        if self.end_date is not None and self.start_date is not None:
            set_date_range(start_date, end_date)
            validate_date_range()
            add_start_url(SITEMAP_URL)

        elif self.start_date is None and self.end_date is None:
            today_time = datetime.today().strftime("%Y-%m-%d")
            self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
            add_start_url(SITEMAP_URL)

        elif self.end_date is not None or self.start_date is not None:
            raise InvalidArgumentException("to use type sitemap give only type sitemap or with start date and end date")

    def handle_article_type():
        if self.article_url is not None:
            add_start_url(self.article_url)
        else:
            raise InputMissingException("type articles must be used with url")

    validate_type()

    if self.type == "sitemap":
        handle_sitemap_type()

    elif self.type == "article":
        handle_article_type()


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
                key, [json.loads(data) if type(json.loads(data)) is dict else json.loads(data)[0]
                      for data in value.getall()
                      if (type(json.loads(data)) is dict and json.loads(data).get('@type') == "NewsArticle")
                      or (type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "NewsArticle")
                      or (type(json.loads(data)) in [list, dict])]

            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall()
                      if (type(json.loads(data)) is dict and json.loads(data).get('@type') == "ImageGallery")
                      or (type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "ImageGallery")]
            )

        elif key == "videoObjects":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall()
                      if (type(json.loads(data)) is dict and json.loads(data).get('@type') == "VideoObject")
                      or (type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "VideoObject")]
            )
        elif key == "imageObjects":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall()
                      if (type(json.loads(data)) is dict and json.loads(data).get('@type') == "ImageObject")
                      or (type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "ImageObject")]
            )
        else:

            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall()
                      if (type(json.loads(data)) is dict and json.loads(data).get('@type') not in
                      ['VideoObject', 'ImageObject', 'NewsArticle'])
                      or (type(json.loads(data)) is list and json.loads(data)[0].get('@type') not in
                          ['VideoObject', 'ImageObject', 'NewsArticle'])]
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


def get_parsed_data(self, response: str, parsed_json_dict: dict) -> dict:

    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in parsed_json_dict.items():
        article_raw_parsed_json_loader.add_value(
            key, [json.loads(data) for data in value.getall()]
        )
    article_data = dict(article_raw_parsed_json_loader.load_item())

    mapper = {"FRA": "France", "fr": "French"}
    tag = response.css('nav.ccmcss_breadcrumb font font::text').getall()
    if tag:
        tag_list = tag
    else:
        tag_list = response.css('nav.ccmcss_breadcrumb div a span::text').getall()

    parsed_data_dict = get_parsed_data_dict()

    if article_data.get("main")[0].get('@type') in ["NewsArticle", "Article"]:
        index = 0
    elif article_data.get("main")[1].get('@type') in ["NewsArticle", "Article"]:
        index = 1

    parsed_data_dict["author"] = [
        {
            "@type": article_data.get('main')[index].get('author').get("@type"),
            "name": article_data.get("main")[index].get('author').get("name"),
            "url": article_data.get("main")[index].get('author').get("url")
        }
    ]
    parsed_data_dict["description"] = [article_data.get("main")[index].get('description')]
    parsed_data_dict["modified_at"] = [article_data.get("main")[index].get('dateModified')]
    parsed_data_dict["published_at"] = [article_data.get("main")[index].get('datePublished')]
    parsed_data_dict["publisher"] = [{
        '@id': article_data.get("main")[index].get('publisher').get('url').split('/')[2],
        '@type': article_data.get("main")[index].get('publisher').get('@type'),
        "name": article_data.get("main")[index].get('publisher').get('name'),

        "logo":{
            "@type": article_data.get("main")[index].get('publisher').get('logo').get("@type"),
            "url": article_data.get("main")[index].get('publisher').get('logo').get("url"),
            'width': {'@type': "Distance",
                      "name": str(article_data.get("main")[index]['publisher']['logo']['width']) + " Px"},
            'height': {'@type': "Distance",
                       'name': str(
                                article_data.get("main")[index]['publisher']['logo']['width']) + " Px"}}}]
    parsed_data_dict["text"] = [article_data.get("main")[index].get("articleBody")]
    parsed_data_dict["thumbnail_image"] = [article_data.get("main")[index].get('image').get('url')]
    parsed_data_dict["title"] = [article_data.get("main")[index].get("headline")]
    parsed_data_dict["images"] = [{"link": article_data.get("main")[index].get('image').get('url'),
                                   "caption": article_data.get('main')[index].get('image').get('name')}]
    parsed_data_dict["source_country"] = ["France"]
    parsed_data_dict["source_language"] = [mapper.get(response.css("html::attr(lang)").get())]
    parsed_data_dict['section'] = [tag_list[1]]
    parsed_data_dict['tags'] = tag_list

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
