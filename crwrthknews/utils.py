""" General functions """

import re
from datetime import timedelta, datetime
import logging
import json
from itertools import zip_longest

from bs4 import BeautifulSoup
from scrapy.loader import ItemLoader
from crwrthknews.items import ArticleRawResponse, ArticleRawParsedJson
from crwrthknews.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)

ERROR_MESSAGES = {
    "InputMissingException": "'{}' field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}

language_mapper = {"zh-tw": "Chinese"}


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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
    if scrape_start_date and scrape_end_date:
        validate_arg(InvalidDateException, not scrape_start_date > scrape_end_date)
        validate_arg(
            InvalidDateException,
            int((scrape_end_date - scrape_start_date).days) <= 30,
        )
    else:
        validate_arg(
            InputMissingException,
            not (scrape_start_date or scrape_end_date),
            "start_date and end_date",
        )
        scrape_start_date = scrape_end_date = datetime.now().date()

    validate_arg(
        InvalidArgumentException, not article_url, "url is not required for sitemap."
    )

    return scrape_start_date, scrape_end_date


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

    validate_arg(InputMissingException, article_url, "url")
    validate_arg(
        InvalidArgumentException,
        not (scrape_start_date or scrape_end_date),
        "start_date and end_date argument is not required for article.",
    )


def date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Return range of all date between given date
    if not end_date then take start_date as end date

    Args:
        start_date (datetime): scrapping start date
        end_date (datetime): scrapping end date
    Returns:
        Value of parameter
    """
    for date in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(date)


def date_in_date_range(published_date, date_range_lst):
    """
    return true if date is in given start date and end date range
    """
    return published_date.date() in date_range_lst


def validate_arg(param_name, param_value, custom_msg=None) -> None:
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
        raise param_name(f"{ERROR_MESSAGES[param_name.__name__]} {custom_msg}")


def based_on_scrape_type(
    scrape_type: str, scrape_start_date: datetime, scrape_end_date: datetime, url: str
) -> datetime:
    """
    check scrape type and based on the type pass it to the validated function,
    after validation return required values.

     Args:
         scrape_type: Name of the scrape type
         scrape_start_date (datetime): scrapping start date
         scrape_end_date (datetime): scrapping end date
         url: url to be used

     Returns:
         datetime: if scrape_type is sitemap
         list: if scrape_type is sitemap
    """
    if scrape_type == "article":
        article_validations(url, scrape_start_date, scrape_end_date)
        return None
    if scrape_type == "sitemap":
        scrape_start_date, scrape_end_date = sitemap_validations(
            scrape_start_date, scrape_end_date, url
        )
        date_range_lst = []
        date_range_lst.extend(iter(date_range(scrape_start_date, scrape_end_date)))
        return date_range_lst

    return validate_arg("MISSING_REQUIRED_FIELD", None, "type")


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
    return remove_empty_elements(dict(article_raw_response_loader.load_item()))


def get_parsed_json_filter(blocks: list, misc: list) -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        blocks: application/ld+json data list
        misc: misc data list
    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_json_flter_dict = {
        "main": None,
        "imageObjects": None,
        "videoObjects": None,
        "other": [],
        "misc": [],
    }
    for block in blocks:
        if "NewsArticle" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(block)
        elif "ImageGallery" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["imageObjects"] = json.loads(block)
        elif "VideoObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["videoObjects"] = json.loads(block)
        else:
            parsed_json_flter_dict["other"].append(json.loads(block))
    parsed_json_flter_dict["misc"] = [json.loads(data) for data in misc]
    return parsed_json_flter_dict


def get_parsed_json(response) -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        response: provided response
    Returns:
        Dictionary with Parsed json response from generated data
    """
    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in get_parsed_json_filter(
        response.css('script[type="application/ld+json"]::text').getall(),
        response.css('script[type="application/json"]::text').getall(),
    ).items():
        article_raw_parsed_json_loader.add_value(key, value)

    return dict(article_raw_parsed_json_loader.load_item())


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


def get_article_json(response: str) -> dict:
    """
    Create json of article using the given response.
    :param response: Input response.
    :type response: str
    :return: Dictionary with all required data.
    :rtype: dict
    """
    parsed_data = {}
    pattern = r"[\r\n\t\"]+"
    parsed_data["source_language"] = [
        language_mapper.get(response.css("html::attr(lang)").get(), None)
    ]
    parsed_data["source_country"] = ["China"]
    header = response.css("h2.itemTitle::text").get()
    time = response.css("div.createddate::text").get()
    description = response.css("div.itemFullText::text").extract()
    description = [re.sub(pattern, "", i) for i in description]
    parsed_data["description"] = response.css(
        "meta[name='description']::attr(content)"
    ).getall()
    image = response.css("img.imgPhotoAfterLoad::attr(src)").get()
    parsed_data["title"] = [header.strip()]
    parsed_data["published_at"] = [time]
    parsed_data["section"] = get_section(response)

    if not image:
        video_object = get_video_json(response)
        if video_object:
            parsed_data["video"] = [video_object]

    else:
        image_object = get_image_json(response)
        if image_object:
            parsed_data["images"] = image_object

    parsed_data["text"] = [" ".join(description)]
    parsed_data["time_parsed"] = str(datetime.now())
    return remove_empty_elements(parsed_data)


def get_image_json(response: str) -> list:
    """
    Create json of image of the article using the given response.
    :param response: Input response.
    :type response: str
    :return: Dictionary with all required data.
    :rtype: dict
    """

    images = []
    if images_link := response.css("img.imgPhotoAfterLoad::attr(src)").getall():
        for link, caption in zip_longest(
            images_link, response.css("img.imgPhotoAfterLoad::attr(alt)").getall()
        ):
            images.append(
                {
                    "link": link,
                    "caption": caption if caption else None,
                }
            )
        return images
    return None


def get_video_json(response: str) -> dict:
    """
    Create json of video of the article using the given response.
    :param response: Input response.
    :type response: str
    :return: Dictionary with all required data.
    :rtype: dict
    """

    video_json = {}
    video_script = response.css("div.itemSlideShow,script::text").getall()
    if video_script:
        video_texts = video_script[10]
        if video_link := re.findall(r"http?.*?\.mp4", video_texts):
            video_json["link"] = video_link[0]
            video_json["thumbnail"] = (
                re.findall(r"http?.*?\.jpg", video_texts)
                if re.findall(r"http?.*?\.jpg", video_texts)
                else None
            )
            video_json["caption"] = response.css(
                "div.detailNewsSlideTitleText::text"
            ).getall()
            return video_json
    return None


def get_section(response: str) -> list:
    """
    Get section using beautifulSoup from the response
    :param response: Input response.
    :type response: str
    :return: list with all required data.
    :rtype: list
    """
    sections = []
    soup = BeautifulSoup(response.body, "html.parser")
    div_items = soup.find_all("div", id="avatar-main-content-inner")

    if div_items:
        for items in div_items:
            for item in items.select("#avatar-pos-main-body"):
                script_text = item.select("script")[1].text
                cleaned_script_text = re.sub(r"[\r\n\t\"]+", "", script_text)
                section = re.findall(r"<a[^>]*>(.*?)</a>", cleaned_script_text)
                sections.append(section[-1])
        return sections
    return None
