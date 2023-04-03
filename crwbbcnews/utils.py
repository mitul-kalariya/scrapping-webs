"""Utility Functions"""
import os
import json
import requests
from datetime import datetime
from scrapy.loader import ItemLoader
from crwbbcnews.constant import SITEMAP_URL
from crwbbcnews.items import ArticleRawResponse, ArticleRawParsedJson
from crwbbcnews.exceptions import InvalidDateException, InvalidArgumentException, InputMissingException


def check_cmd_args(self, start_date: str, end_date: str) -> None:
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
        if self.type not in ["article", "sitemap", "link_feed"]:
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
        json.dump(file_data, file, indent=4, ensure_ascii=False)


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
                key,
                [json.loads(data) if type(json.loads(data)) is dict else json.loads(data)[0] for data in value.getall()
                 if (type(json.loads(data)) is dict and json.loads(data).get('@type') == "NewsArticle") or (
                             type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "NewsArticle") or (
                             type(json.loads(data)) in [list, dict])]

            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if
                      (type(json.loads(data)) is dict and json.loads(data).get('@type') == "ImageGallery") or (
                                  type(json.loads(data)) is list and json.loads(data)[0].get(
                              '@type') == "ImageGallery")]
            )

        elif key == "VideoObject":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if
                      (type(json.loads(data)) is dict and json.loads(data).get('@type') == "VideoObject") or (
                                  type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "VideoObject")]
            )
        elif key == "misc":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall()])
        else:
            try:
                for data in value.getall():
                    data_dict = json.loads(data)
                    data_type = data_dict.get('@graph')[0].get('@type')
                    if data_dict is dict and data_type not in selector_and_key.keys() and data_type != "NewsArticle":
                        article_raw_parsed_json_loader.add_value(key, data_dict)
            except:
                pass

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


def get_data_from_json(response, parsed_main):
    """
    Get data from output response
    """
    url = response.url
    response = requests.get(f'{url}.json').json()
    parsed_json = {}
    raw_text = ''
    images, tags, topics = [], [], []

    for block in response['content']['blocks']:
        if block['type'] == 'paragraph' or block['type'] == 'crosshead':
            raw_text = raw_text + f'{block["text"]}\n'

        if block['type'] == 'image':
            image_dict = {
                "link": block.get('href'),
                "caption": block.get('altText')
            }
            images.append(image_dict)

    for tag_block in response.get('metadata').get('tags').get('about'):
        tags.append(tag_block['topicName'])

    for section_block in response['metadata']['topics']:
        topics.append(section_block['topicName'])

    parsed_json['section'] = topics
    parsed_json['tags'] = tags
    parsed_json['author'] = [parsed_main['main']['@graph'][0]['author']]
    parsed_json['thumbnail_image'] = [response.get('promo').get('indexImage').get('href')]
    parsed_json['images'] = images
    parsed_json['text'] = [raw_text]
    parsed_json['title'] = [response.get('promo').get('headlines').get('headline')]
    parsed_json['description'] = [parsed_main['main']['@graph'][0]['description']]
    parsed_json['modified_at'] = [parsed_main['main']['@graph'][0]['dateModified']]
    parsed_json['published_at'] = [parsed_main['main']['@graph'][0]['datePublished']]
    parsed_json['source_language'] = [response.get('metadata').get('passport').get('language')]
    parsed_json['source_country'] = ['China']
    parsed_json['publisher'] = [parsed_main['main']['@graph'][0]['publisher']]

    return remove_empty_elements(parsed_json)