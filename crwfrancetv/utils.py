import json
import os
from datetime import datetime
from scrapy.loader import ItemLoader
from crwfrancetv.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from crwfrancetv.constant import SITEMAP_URL
from crwfrancetv.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)


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
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "NewsArticle"]
            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "ImageGallery"]
            )

        elif key == "videoObjects":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data).get('video') for data in value.getall()[:1] if
                      json.loads(data).get('video') and json.loads(data).get('video').get("@type") == "VideoObject"]
            )
        elif key == "imageObjects":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data).get('video')
                      for data in value.getall()[:1]
                      if json.loads(data).get('video') and (json.loads(data).get('video').get("@type") == "ImageObject"
                                                            or json.loads(data).get('video').get("@type")
                                                            == "ImageGallery")]
            )
        else:
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type')
                      in list(selector_and_key.keys()) or json.loads(data).get('@type') != "NewsArticle"]
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
    parsed_data_dict = get_parsed_data_dict()
    article_data = dict(article_raw_parsed_json_loader.load_item())
    mapper = {"FRA": "France", "fr": "French"}
    article_data["title"] = response.css('h1.c-title ::text').get()
    article_data["section"] = response.css('li.breadcrumb__item a::text').getall()
    selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
    article_data["json_data"] = [json.loads(data) for data in selector]
    language = response.css("html::attr(lang)").get()
    article_data["language"] = mapper.get(language)
    article_data["country"] = mapper.get("FRA")

    parsed_data_dict["source_country"] = ["France"]
    parsed_data_dict["source_language"] = [mapper.get(response.css("html::attr(lang)").get())]

    if len([article_data.get("main").get('author')]) == 1:
        if type(article_data.get("main").get('author')) == list:
            parsed_data_dict["author"] = [{
                "@type": article_data.get("main").get('author')[0].get("@type"),
                "name": article_data.get("main").get('author')[0].get("name"),
                "url": article_data.get("main").get('author')[0].get("url")
            }]
        else:
            if type(article_data.get("main").get('author')) == dict:
                parsed_data_dict["author"] = [{
                    "@type": article_data.get("main").get('author').get("@type"),
                    "name": article_data.get("main").get('author').get("name"),
                    "url": article_data.get("main").get('author').get("url")
                }]
    else:
        author_list = []
        for i in range(len(article_data.get("main").get('author'))):
            author_list.append({
                "@type": article_data.get("main").get('author')[i].get("@type"),
                "name": article_data.get("main").get('author')[i].get("name"),
                "url": article_data.get("main").get('author')[i].get("url")
            })
        parsed_data_dict["author"] = [author_list]

    parsed_data_dict["description"] = [article_data.get("main").get('description')]
    parsed_data_dict["modified_at"] = [article_data.get("main").get('dateModified')]
    parsed_data_dict["published_at"] = [article_data.get("main").get('datePublished')]

    if "publisher" in list(article_data.get("main").keys()):
        key = "publisher"
    elif "Publisher" in list(article_data.get("main").keys()):
        key = "Publisher"

    parsed_data_dict["publisher"] = [
        {
            '@type': article_data.get("main").get(key).get('@type'),
            'url': article_data.get("main").get(key).get('url'),
            "logo": {
                "@type": article_data.get("main").get(key).get("logo").get('@type'),
                "url": article_data.get("main").get(key).get("logo").get('url'),
                'width': {'@type': "Distance",
                          "name": str(article_data.get("main").get(key).get('logo').get('width').get('value')) + " Px"},
                'height': {'@type': "Distance", 'name': str(
                    article_data.get("main").get(key).get('logo').get('height').get('value')) + " Px"}}}]

    parsed_data_dict["text"] = [article_data.get("main").get('articleBody')]

    if type(article_data.get("main").get('image')) is str:
        parsed_data_dict["thumbnail_image"] = [article_data.get("main").get('image')]
        parsed_data_dict["images"] = [{"link": article_data.get("main").get('image')}]

    else:
        for img_data in article_data.get("main").get('image'):
            if img_data is not None:
                parsed_data_dict["thumbnail_image"] = [img_data.get('url')]

                parsed_data_dict["images"] = [{"link": img_data.get('url'),
                                               "caption": img_data.get('name')}]

                break

    if not article_data.get("title") or article_data.get("title") == '':
        parsed_data_dict["title"] = [article_data.get("main").get("headline")]
    else:
        parsed_data_dict["title"] = [article_data.get("title")]

    parsed_data_dict["section"] = [each.strip() for each in article_data.get('section') if each.strip() != '']
    parsed_data_dict["tags"] = article_data.get("main").get('keywords').split(',')
    parsed_data_dict['embedded_video_link'] = [article_data.get("video")]

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
