import json
from datetime import datetime
from scrapy.loader import ItemLoader

from crwcp24.constant import SITEMAP_URL
from crwcp24.exceptions import (
    InputMissingException,
    InvalidArgumentException,
    InvalidDateException,
)
from crwcp24.items import ArticleRawParsedJson, ArticleRawResponse
from crwcp24.videos import get_video


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
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")

    def validate_date_range():
        if self.start_date > self.end_date:
            raise InvalidDateException("start_date must be less then end_date")
        if (self.end_date - self.start_date).days > 30:
            raise InvalidDateException(
                "Enter start_date and end_date for maximum 30 days."
            )

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
            self.today_date = datetime.strptime(today_time, "%Y-%m-%d")
            add_start_url(SITEMAP_URL)

        elif self.end_date is not None or self.start_date is not None:
            raise InvalidArgumentException(
                "to use type sitemap give only type sitemap or with start date and end date"
            )

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
                key,
                [
                    json.loads(data)
                    for data in value.getall()
                    if json.loads(data).get("@type") == "NewsArticle"
                ],
            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key,
                [
                    json.loads(data)
                    for data in value.getall()
                    if json.loads(data).get("@type") == "ImageGallery"
                ],
            )

        elif key == "videoObjects":
            article_raw_parsed_json_loader.add_value(
                key,
                [
                    json.loads(data)
                    for data in value.getall()
                    if json.loads(data).get("@type") == "VideoObject"
                ],
            )
        elif key == "imageObjects":
            article_raw_parsed_json_loader.add_value(
                key,
                [
                    json.loads(data)
                    for data in value.getall()
                    if json.loads(data).get("@type") == "ImageObject"
                ],
            )
        else:
            article_raw_parsed_json_loader.add_value(
                key,
                [
                    json.loads(data)
                    for data in value.getall()
                    if json.loads(data).get("@type") in ["ImageObject", "VideoObject"]
                    and json.loads(data).get("@type") != "NewsArticle"
                ],
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

    mapper = {"CA": "Canada", "en": "English"}
    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in parsed_json_dict.items():
        article_raw_parsed_json_loader.add_value(
            key, [json.loads(data) for data in value.getall()]
        )
    article_data = dict(article_raw_parsed_json_loader.load_item())
    article_data["title"] = response.css("h1.articleHeadline::text").get()
    article_data["img_url"] = response.css("div.article div.image img::attr(src)").get()
    article_data["img_caption"] = response.css("div.article div.image p::text").get()
    article_data["author_url"] = response.css('div.prof a::attr("href")').get()
    article_data["text"] = " ".join(response.css("div.articleBody > p::text").getall())
    section_meta = response.xpath('//meta[@property="article:section"]')
    article_data["section_content"] = section_meta.xpath("@content").get()
    language = response.css("html::attr(lang)").get()

    if response.css("div.aritcleVideoContainer"):
        article_data["video_url"] = get_video(self, response.url)

    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict["author"] = [
        {
            "@type": article_data.get("main").get("author")[0].get("@type"),
            "name": article_data.get("main").get("author")[0].get("name"),
            "url": article_data.get("author_url"),
        }
    ]
    parsed_data_dict["description"] = [article_data.get("main").get("description")]
    parsed_data_dict["modified_at"] = [article_data.get("main").get("dateModified")]
    parsed_data_dict["published_at"] = [article_data.get("main").get("datePublished")]
    parsed_data_dict["publisher"] = [
        {
            "@id": article_data.get("other")[1].get('url').split('//')[1],
            "@type": article_data.get("main").get("publisher").get("@type"),
            "name": article_data.get("main").get("publisher").get("name"),
            "logo": {
                "@type": article_data.get("main")
                .get("publisher")
                .get("logo")
                .get("@type"),
                "url": article_data.get("main").get("publisher").get("logo").get("url"),
                "width": {
                    "@type": "Distance",
                    "name": str(
                        article_data.get("main")
                        .get("publisher")
                        .get("logo")
                        .get("width")
                    )
                    + " Px",
                },
                "height": {
                    "@type": "Distance",
                    "name": str(
                        article_data.get("main")
                        .get("publisher")
                        .get("logo")
                        .get("height")
                    )
                    + " Px",
                },
            },
        }
    ]
    parsed_data_dict["text"] = [article_data.get("text")]
    parsed_data_dict["thumbnail_image"] = [
        article_data.get("main").get("image").get("url")
    ]
    parsed_data_dict["title"] = [article_data.get("title")]
    body_img_url = response.css('div.articleBody p img::attr("src")').getall()
    body_img_caption = response.css('div.articleBody p img::attr("alt")').getall()
    parsed_data_dict["images"] = [
        {"link": article_data.get("other")[-1].get("url") + link, "caption": caption}
        for link, caption in zip(body_img_url, body_img_caption)
    ]
    parsed_data_dict["images"].append(
        {
            "link": article_data.get("img_url"),
            "caption": article_data.get("img_caption"),
        }
    )
    parsed_data_dict["section"] = [article_data.get("section_content")]
    parsed_data_dict["embed_video_link"] = [article_data.get("video_url")]

    if not language:
        language = mapper.get("en")
    parsed_data_dict["source_language"] = [mapper.get(language)]
    parsed_data_dict["source_country"] = [mapper.get("CA")]
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