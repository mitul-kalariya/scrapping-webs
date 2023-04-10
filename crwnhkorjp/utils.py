import json
import os
from datetime import datetime
from scrapy.loader import ItemLoader
from crwnhkorjp.constant import SITEMAP_URL
from crwnhkorjp.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from crwnhkorjp.exceptions import (
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
        if self.url is not None:
            add_start_url(self.url)
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
                key, [json.loads(data) for data in value.getall() if "NewsArticle" in json.loads(data).get('@type')]
            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "ImageGallery"]
            )

        elif key == "videoObjects":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "VideoObject"]
            )
        elif key == "imageObjects":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type')
                      in ["ImageObject", "ImageGallery"]]
            )
        else:
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') not in
                      selector_and_key.keys() and json.loads(data).get('@type') != "NewsArticle"]
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

    parsed_data_dict = get_parsed_data_dict()
    text = response.css('p.content--summary-more::text').getall()
    text_summary = response.css('p.content--summary::text').getall()
    body_text = response.css('div.body-text::text').getall()
    body_img = response.css('figure.body-img img::attr("data-src")').getall()
    mapper = {"ja": "Japanse"}
    if "other" not in list(parsed_json_dict.keys()):
        section = response.css('a.c-header-menu__link::text').getall()[1]
        parsed_data_dict["source_country"] = ["Japan"]
        parsed_data_dict["source_language"] = [mapper.get(response.css('meta[name="content-language"]\
                                                                    ::attr(content)').get())]

        parsed_data_dict["author"] = [parsed_json_dict.get('main').get('author')]
        parsed_data_dict["description"] = [parsed_json_dict.get('main').get('description')]
        parsed_data_dict["modified_at"] = [parsed_json_dict.get('main').get('dateModified')]
        parsed_data_dict["published_at"] = [parsed_json_dict.get("main").get('datePublished')]
        parsed_data_dict["publisher"] = [
            {
                '@id': parsed_json_dict.get("main").get("url").split('/')[2],
                '@type': parsed_json_dict.get("main").get('@type'),
                'name': parsed_json_dict.get("main").get('name'),
                'logo': {
                    "@type": parsed_json_dict.get("main").get('publisher').get('logo').get('@type'),
                    "url": parsed_json_dict.get("main").get('publisher').get('logo').get('url'),
                    'width': {
                        '@type': "Distance",
                        "name": str(parsed_json_dict.get("main").get('publisher').get('logo').get('width')) + " Px"},
                    'height': {
                        '@type': "Distance",
                        'name': str(parsed_json_dict.get("main").get('publisher').get('logo').get('height')) + " Px"}}
            }
        ]
        parsed_data_dict["text"] = [" ".join(text + text_summary + body_text)]
        parsed_data_dict["thumbnail_image"] = [parsed_json_dict.get("main").get("url").split('/')[2]
                                               + parsed_json_dict.get("main").get('image').get('url')]
        parsed_data_dict["title"] = [parsed_json_dict.get('main').get('headline')]
        parsed_data_dict["images"] = [{"link": parsed_json_dict.get("main").get("url").split('/')[2] + img}
                                      for img in body_img]
        parsed_data_dict["images"].append({"link": parsed_json_dict.get("main").get("url").split('/')[2]
                                           + parsed_json_dict.get("main").get('image').get('url')})
        parsed_data_dict["section"] = [section]
        parsed_data_dict["tags"] = parsed_json_dict.get('main').get('keywords')
        if "videoObjects" in list(parsed_json_dict.keys()):
            parsed_data_dict["embed_video_link"] = [parsed_json_dict.get("other")[1].get("url")[:-1] + response.css(
                "iframe.video-player-fixed::attr('src')").get()]

    else:
        parsed_data_dict["source_country"] = ["Japan"]
        parsed_data_dict["source_language"] = [mapper.get(response.css('meta[name="content-language"]\
                                                                    ::attr(content)').get())]

        parsed_data_dict["author"] = [{"@type": parsed_json_dict.get("other")[1].get("@type"),
                                       "name": parsed_json_dict.get("other")[1].get("name"),
                                       "url": parsed_json_dict.get("other")[1].get("url")}]
        parsed_data_dict["description"] = [parsed_json_dict.get("main").get('description')]
        parsed_data_dict["modified_at"] = [parsed_json_dict.get("main").get("dateModified")]
        parsed_data_dict["published_at"] = [parsed_json_dict.get("main").get('datePublished')]
        parsed_data_dict["publisher"] = [
            {
                '@id': parsed_json_dict.get("other")[1].get("url").split('/')[2],
                '@type': parsed_json_dict.get("other")[0].get('@type'),
                'name': parsed_json_dict.get("other")[0].get('name'),
                'logo': {
                    "@type": parsed_json_dict.get("other")[0].get('logo').get('@type'),
                    "url": parsed_json_dict.get("other")[0].get('logo').get('url'),
                    'width': {
                        '@type': "Distance",
                        "name": str(parsed_json_dict.get("other")[0].get('logo').get('width')) + " Px"},
                    'height': {
                        '@type': "Distance",
                        'name': str(parsed_json_dict.get("other")[0].get('logo').get('height')) + " Px"}}
            }
        ]
        parsed_data_dict["text"] = [" ".join(text + text_summary + body_text)]
        parsed_data_dict["thumbnail_image"] = [parsed_json_dict.get("main").get('image')[0].get('url')]
        parsed_data_dict["title"] = [parsed_json_dict.get('main').get('headline')]
        parsed_data_dict["images"] = [{"link": parsed_json_dict.get("other")[1].get("url")[:-1] + img}
                                      for img in body_img]
        parsed_data_dict["images"].append({"link": parsed_json_dict.get("main").get('image')[0].get('url')})
        parsed_data_dict["section"] = [parsed_json_dict.get("main").get('articleSection')]
        parsed_data_dict["tags"] = parsed_json_dict.get('main').get('keywords')
        if "videoObjects" in list(parsed_json_dict.keys()):
            parsed_data_dict["embed_video_link"] = [parsed_json_dict.get("other")[1].get("url")[:-1] + response.css(
                "iframe.video-player-fixed::attr('src')").get()]
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
        json.dump(file_data, file, indent=4, ensure_ascii=False)
