import json
import os
import pdb
from datetime import datetime
from urllib.parse import urlparse

from scrapy.http import Response
from .exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)
from w3lib.html import remove_tags
from crwleparisien.constant import (
    SITEMAP_URL,
    DATE_FORMAT,
    TYPE,
    PARSED_DATA_KEYS_LIST,
)
from crwleparisien.itemLoader import (
    ArticleRawResponseLoader,
    ArticleRawParsedJsonLoader
)
from crwleparisien.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)


def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (LeParisien): The ZeitDeNews spider instance.
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

    validate_type(self)

    if self.type == "sitemap":
        handle_sitemap_type(self, start_date, end_date, SITEMAP_URL)

    elif self.type == "article":
        handle_article_type(self)


def add_start_url(self, url):
    self.start_urls.append(url)


def set_date_range(self, start_date, end_date):
    self.start_date = datetime.strptime(start_date, DATE_FORMAT)
    self.end_date = datetime.strptime(end_date, DATE_FORMAT)


def validate_date_range(self):
    if self.start_date > self.end_date:
        raise InvalidDateException("start_date must be less then end_date")
    if (self.end_date - self.start_date).days > 30:
        raise InvalidDateException("Enter start_date and end_date for maximum 30 days.")


def validate_type(self):
    if self.type not in ["article", "sitemap"]:
        raise InvalidArgumentException("type should be articles or sitemap")


def handle_sitemap_type(self, start_date, end_date, initial_url):
    if self.end_date is not None and self.start_date is not None:
        set_date_range(self, start_date, end_date)
        validate_date_range(self)
        add_start_url(self, initial_url)

    elif self.start_date is None and self.end_date is None:
        today_time = datetime.today().strftime(DATE_FORMAT)
        self.today_date = datetime.strptime(today_time, DATE_FORMAT)
        add_start_url(self, initial_url)

    elif self.end_date is not None or self.start_date is not None:
        raise InvalidArgumentException("to use type sitemap give only type sitemap or with start date and end date")


def handle_article_type(self):
    if self.url is not None:
        add_start_url(self, self.url)
    else:
        raise InputMissingException("type articles must be used with url")


def get_raw_response(response: str, selector_and_key: dict) -> dict:
    """
    Raw response data generated from given response and selector
    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector
    Returns:
        Dictionary with generated raw response
    """
    article_raw_response_loader = ArticleRawResponseLoader(
        item=ArticleRawResponse(), response=response
    )
    for key, value in selector_and_key.items():
        article_raw_response_loader.add_value(key, value)
    return dict(article_raw_response_loader.load_item())


def get_parsed_json(selector_and_key: dict) -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector
    Returns:
        Dictionary with Parsed json response from generated data
    """

    article_raw_parsed_json_loader = ArticleRawParsedJsonLoader(
        item=ArticleRawParsedJson()
    )

    for key, value in selector_and_key.items():
        article_raw_parsed_json_loader.add_value(
            key, [json.loads(data) for data in value.getall()]
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
    return dict.fromkeys(PARSED_DATA_KEYS_LIST, None)


def get_parsed_data(self, response: Response, parsed_json_data: dict) -> dict:
    parsed_data_dict = get_parsed_data_dict()
    published_date = response.css('meta[property="article:published_time"]::attr(content)').get()
    modified_date = response.css('meta[property="article:modified_time"]::attr(content)').get()
    img_url = response.css("div.width_full >figure > div.pos_rel > img::attr('src')").getall()
    text = response.css('section.content > p::text').getall()
    mapper = {"FRA": "France", "fr-FR": "French"}
    title = response.css('header.article_header > h1::text').getall()
    category = response.css('div.breadcrumb > a::text').getall()
    language = response.css("html::attr(lang)").get()

    parsed_data_dict["source_country"] = [mapper.get("FRA")]
    parsed_data_dict["source_language"] = [mapper.get(language)]

    article_author_url = response.css('a.author_link::attr(href)').getall()
    main = parsed_json_data.get("main")
    other = parsed_json_data.get("other")

    parsed_data_dict["author"] = get_author(other[0], other, article_author_url)
    parsed_data_dict["description"] = [main.get('description')]

    parsed_data_dict["modified_at"] = get_modified_at(other[0], modified_date)
    parsed_data_dict["published_at"] = get_published_at(other[0], published_date)
    parsed_data_dict["publisher"] = get_publisher(other[0])

    parsed_data_dict["text"] = get_text(other[0], text)

    parsed_data_dict["thumbnail_image"] = get_thumbnail_image(other[0], other,
                                                              img_url)
    parsed_data_dict["title"] = title
    parsed_data_dict["images"] = get_image(other[0], response)
    parsed_data_dict["section"] = "".join(category).split(",")

    parsed_data_dict["tags"] = get_tags(other[0])
    parsed_data_dict['embed_video_link'] = get_video(response)

    return remove_empty_elements(parsed_data_dict)


def is_live_blog(main):
    return main.get(TYPE) == "LiveBlogPosting"


def get_thumbnail_image(main, other, img_url):
    if is_live_blog(main):
        return main.get("thumbnailUrl")
    else:
        return [other[1].get('url') + img_url[0][1:]]


def get_tags(main):
    if is_live_blog(main):
        return None
    else:
        return main.get("keywords")


def get_text(main, text):
    if is_live_blog(main):
        blog_list = main.get("liveBlogUpdate")
        text_live_blog = list(map(lambda x: remove_tags(x.get("articleBody")), blog_list))
        return text_live_blog
    else:
        return ["".join(text)]


def get_published_at(main, published_date):
    if is_live_blog(main):
        return [published_date]
    else:
        return [main.get('datePublished')]


def get_modified_at(main, modified_date):
    if is_live_blog(main):
        return [modified_date]
    else:
        return [main.get('datePublished')]


def get_video(response):
    video_link = response.css('iframe.dailymotion-player::attr(src)').getall()
    if video_link:
        return [video_link]


def get_author(main, other, article_author_url) -> list:
    author_list = []
    if is_live_blog(main):
        for blog in main.get("liveBlogUpdate"):
            author_dict = get_author_dict(blog)
            author_list.append(author_dict)
    else:
        author_dict = get_author_dict(main.get("author"))

        if article_author_url and len(other) > 1:
            author_dict["url"] = other[1].get("url") + article_author_url[0][1:]

        author_list.append(author_dict)
    return [author_list[0]]


def get_author_dict(author):
    author_dict = {
        TYPE: author.get("author")[0].get(TYPE),
        "name": author.get("author")[0].get("name")
    }
    return author_dict


def get_publisher(main):
    publisher_list = []
    publisher_dict = {
        TYPE: main.get('publisher').get(TYPE),
        'name': main.get('publisher').get('name'),

        'logo': {
            TYPE: main.get('publisher').get('logo').get(TYPE),
            'url': main.get('publisher').get('logo').get('url'),

            'width': {
                TYPE: "Distance",
                "name": str(main.get('publisher').get('logo').get('width')) + " Px"},

            'height': {
                TYPE: "Distance",
                'name': str(main.get('publisher').get('logo').get('height')) + " Px"}}
    }
    publisher_list.append(publisher_dict)
    return publisher_list


def get_image(main, response):
    if is_live_blog(main):
        img_url = main.get("image").get("url")
        img_dict = {
            "link": img_url
        }
    else:
        leparisien_main_domain = get_domain(response)
        img_url = response.css("div.width_full >figure > div.pos_rel > img::attr('src')").getall()
        img_caption = response.css('div.width_full >figure > figcaption > span::text').getall()
        img_dict = {
            "link": leparisien_main_domain + img_url[0][1:],
            "caption": img_caption[0],
        }
    return [img_dict]


def get_domain(response):
    parsed_uri = urlparse(response.url)
    domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
    return domain


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
