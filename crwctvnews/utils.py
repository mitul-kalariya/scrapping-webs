""" General functions """
from datetime import timedelta, datetime
import json
import os
import re

from scrapy.loader import ItemLoader

from crwctvnews.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from .exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)

ERROR_MESSAGES = {
    "InputMissingException": "This field is required :-",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}
language_mapper = {"en": "English"}


# Regex patterns
SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"


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


def date_in_date_range(published_date: datetime, date_range_lst: list[datetime]) -> bool:
    """return true if date is in given start date and end date range
    Args:
        published_date : Article published date
        date_range_lst : List of datetime object

    Returns:
        True or Flase
    """
    return published_date.date() in date_range_lst


def validate_arg(param_name: str, param_value: str, custom_msg: str = None) -> None:
    """
    Validate the param.
    Args:
        param_name: Name of the parameter to be validated
        param_value: Value of the required parameter
        custom_msg: custom error message

    Raises:
        ValueError if not provided
    Returns:
          Value of parameter
    """
    if not param_value:
        raise ValueError(f"{ERROR_MESSAGES[param_name.__name__]} {custom_msg}")


def validate(
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
        return None, None
    if scrape_type == "sitemap":
        scrape_start_date, scrape_end_date = sitemap_validations(
            scrape_start_date, scrape_end_date, url
        )
        date_range_lst = []
        date_range_lst.extend(iter(date_range(scrape_start_date, scrape_end_date)))
        return scrape_start_date, date_range_lst

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
    return dict(article_raw_response_loader.load_item())


def get_parsed_json_filter(blocks: list, misc: list, regex_pattern: str = "") -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        blocks: application/ld+json data list
        misc: misc data list
        regex_pattern: pattern to remove that type of string
    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_json_flter_dict = {
        "main": None,
        "ImageGallery": None,
        "VideoObject": None,
        "Other": [],
        "misc": [],
    }
    for block in blocks:
        space_removed_block = re.sub(regex_pattern, "", block).strip()
        if "NewsArticle" in json.loads(space_removed_block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(space_removed_block)
        elif "ImageGallery" in json.loads(space_removed_block).get("@type", [{}]):
            parsed_json_flter_dict["ImageGallery"] = json.loads(space_removed_block)
        elif "VideoObject" in json.loads(space_removed_block).get("@type", [{}]):
            parsed_json_flter_dict["VideoObject"] = json.loads(space_removed_block)
        else:
            parsed_json_flter_dict["Other"].append(json.loads(space_removed_block))
    parsed_json_flter_dict["misc"] = [json.loads(re.sub(regex_pattern, "", data).strip()) for data in misc]
    return parsed_json_flter_dict


def get_parsed_json(response: str) -> dict:
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

    for key, value in get_parsed_json_filter(
        response.css('script[type="application/ld+json"]::text').getall(),
        response.css('script[type="application/json"]::text').getall(),
        SPACE_REMOVER_PATTERN
    ).items():
        article_raw_parsed_json_loader.add_value(key, value)

    return dict(article_raw_parsed_json_loader.load_item())


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
            f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )

    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)

    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)


def get_parsed_data_dict() -> dict:
    """
    Return base data dictionary
    Args:
    None

    Returns:
        dict: Return base data dictionary
    """
    return {
        "source_country": None,
        "source_language": None,
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


def get_parsed_data(response: str, parsed_json_main: list) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """
    data_dict = get_author_and_publisher_details(parsed_json_main)
    image = get_image_url(response)

    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= {
        "source_country": ["India"],
        "source_language": [language_mapper.get(response.css("html::attr(lang)").get())],
    }
    caption = response.css(".c-text span::text").getall()

    video_url = response.css("inline-video::attr('axis-ids')").get()
    video_link = None
    if video_url:
        video_url = (video_url.split('axisId":')[-1].split('"}')[0].replace('"', ""))
        video_link = "https://www.ctvnews.ca/video?clipId=" + video_url

    parsed_data_dict |= {"author": data_dict.get("author")}
    parsed_data_dict |= {"description": [data_dict.get("alternativeheadline")]}
    parsed_data_dict |= {"modified_at": [data_dict.get("modified_date")]}
    parsed_data_dict |= {"published_at": [data_dict.get("published_date")]}
    parsed_data_dict |= {"publisher": get_publisher_detail(response, data_dict)}
    parsed_data_dict |= {
        "title": [data_dict.get("headline")],
        "text": [re.sub(SPACE_REMOVER_PATTERN, "", " ".join(
            response.css(".twitter-tweet::text, .c-text p::text").getall()),)],
        "section": response.css(".c-breadcrumb__item__link span::text").getall()
    }
    parsed_data_dict |= {
        "images": [{"link": data_dict.get("image_url")}] if data_dict.get("image_url")
        else [{"link": image, "caption": caption}],
        "video": [{"link": video_link}],
        "thumbnail_image": [data_dict.get("thumbnail_url")],
    }
    return parsed_data_dict


def get_author_and_publisher_details(block: dict) -> dict:
    """
    get author and publisher details
    Args:
        blocks: json/+ld data
    Returns:
        str : author and publisher details
    """
    data_dict = {}
    data_dict["publisher_name"] = block.get("publisher", None).get("name", None)
    data_dict["publisher_type"] = block.get("publisher", None).get(
        "@type", None
    )
    data_dict["published_date"] = block.get("datePublished", None)
    data_dict["modified_date"] = block.get("dateModified", None)
    data_dict["headline"] = block.get("headline", None)
    data_dict["alternativeheadline"] = block.get("description", None)
    data_dict["thumbnail_url"] = block.get("thumbnailUrl", None)

    if "News" in block.get("@type") and block.get("author"):
        data_dict["author"] = data_dict.get("author", [])
        for author in block.get("author"):
            auth = {}
            auth["name"] = author.get("name")
            auth["@type"] = author.get("@type")
            auth["url"] = author.get("sameAs")
            data_dict["author"].append(auth)
    data_dict["image_url"] = block.get("image", None).get("url", None)
    return data_dict


def get_publisher_detail(response, data_dict: dict) -> dict:
    """generate publisher detail and return dict

    Args:
        response: reponse object scrapy
        data_dict (dict): data_dict which contains info of main

    Returns:
        dict: details of publisher to pass to json
    """
    return [{
            "@id": "www.ctvnews.ca",
            "@type": data_dict.get("publisher_type"),
            "name": data_dict.get("publisher_name"),
            "logo": {
                "type": "ImageObject",
                "url": "https://www.ctvnews.ca/"
                + f'{response.css(".c-quickArticle__header_logo::attr(src)").get()}', }
            }]


def get_image_url(response) -> str:
    """return image url from response

    Args:
        response : response object of scrapy

    Returns:
        str: return link of image
    """
    image = None
    imageurl = response.css(".inline-image::attr(src)").getall()
    for img in imageurl:
        image = img if "https://www.ctvnews.ca/" in img else f"https://www.ctvnews.ca/{img}"
    return image


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """Recursively remove empty lists, empty dicts, or None elements from a dictionary.

    Args:
        parsed_data_dict (dict): Input dictionary.
    Returns:
        dict: Dictionary with all empty lists, and empty dictionaries removed.
    """

    def empty(value):
        return value is None or value == {} or value == [] or value == ""

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
