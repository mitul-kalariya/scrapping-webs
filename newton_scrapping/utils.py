""" General functions """
from datetime import timedelta, datetime
import json
import os

from scrapy.loader import ItemLoader

from newton_scrapping.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from .exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)

ERROR_MESSAGES = {
    "InputMissingException": "{} field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}

language_mapper = {"en": "English", "en-ca": "English (Canada)"}


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


def date_in_date_range(published_date: datetime, date_range_lst: list) -> bool:
    """
    return true if date is in given start date and end date range

    Args:
        published_date (datetime): published date for checking exsist or not in date range list
        date_range_lst (list): date range list
    Returns:
        Value of parameter
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
        raise param_name(ERROR_MESSAGES[param_name.__name__].format(custom_msg))


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
        "ImageGallery": None,
        "VideoObject": None,
        "Other": [],
        "misc": [],
    }
    for block in blocks:
        if "NewsArticle" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(block)
        elif "ImageGallery" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["ImageGallery"] = json.loads(block)
        elif "VideoObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["VideoObject"] = json.loads(block)
        else:
            parsed_json_flter_dict["Other"].append(json.loads(block))
    parsed_json_flter_dict["misc"].append(misc)
    return parsed_json_flter_dict


def get_parsed_json(response) -> dict:
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


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param parsed_data_dict: Input dictionary.
    :type parsed_data_dict: dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
    :rtype: dict
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
    text = response.css("p.c-article-body__text::text").getall()
    image = {
        "link": data_dict.get("image_url"),
        "caption": data_dict.get("image_caption")
    }

    caption = response.css(".c-text span::text").getall()

    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= {
        "source_country": ["Canada"],
        "source_language": [language_mapper.get(
            response.css("html::attr(lang)").get().lower(),
            response.css("html::attr(lang)").get()
        )],
    }

    parsed_data_dict |= {"author": data_dict.get("author")}
    parsed_data_dict |= {"description": [data_dict.get("description")]}
    parsed_data_dict |= {"modified_at": [data_dict.get("modified_at")]}
    parsed_data_dict |= {"published_at": [data_dict.get("published_at")]}
    parsed_data_dict |= {"publisher": get_publisher_detail(response, data_dict)}
    parsed_data_dict |= {
        "title": [data_dict.get("title")],
        "text": [" ".join(text)],
        "thumbnail_image": [data_dict.get("thumbnail_image")]
    }
    parsed_data_dict |= {
        "images": [image] or [{"link": image, "caption": caption}],
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
    data_dict = {
        "description": block.get("description"),
        "modified_at": block.get("dateModified"),
        "published_at": block.get("datePublished"),
        "publisher_id": block.get("publisher", {}).get("@id"),
        "publisher_type": block.get("publisher", {}).get("@type"),
        "publisher_name": block.get("publisher", {}).get("name"),
        "logo_type": block.get("publisher", {}).get("logo", {}).get("@type"),
        "logo_url": block.get("publisher", {}).get("logo", {}).get("url"),
        "logo_width": block.get("publisher", {}).get("logo", {}).get("width"),
        "logo_height": block.get("publisher", {}).get("logo", {}).get("height"),
        "title": block.get("headline", {}),
        "image_url": block.get("image", {}).get("url"),
        "image_caption": block.get("image", {}).get("description"),
        "thumbnail_image": block.get("thumbnailUrl"),
        "headline": block.get("headline"),
    }
    data_dict["author"] = []
    if block.get("author"):
        for author in block.get("author"):
            data_dict["author"].append({
                "@type": author.get("@type"),
                "name": author.get("name"),
                "url": author.get("url")
            })
    else:
        data_dict.get("author", []).append({
            "name": block.get("author"),
            "@type": block.get("@type")
        })
    return data_dict


def get_publisher_detail(response: str, data_dict: dict) -> dict:
    """generate publisher detail and return dict

    Args:
        response: reponse object scrapy
        data_dict (dict): data_dict which contains info of main

    Returns:
        dict: details of publisher to pass to json
    """
    return [{
            "@id": data_dict.get("publisher_id", "www.theglobeandmail.com"),
            "@type": data_dict.get("publisher_type"),
            "name": data_dict.get("publisher_name"),
            "logo": {
                "type": data_dict.get("logo_type", "ImageObject"),
                "url": data_dict.get("logo_url"),
                "width": {
                    "@type": "Distance",
                    "name": f"{data_dict.get('logo_width')} px"
                } if data_dict.get("logo_width") else None,
                "height": {
                    "@type": "Distance",
                    "name": f"{data_dict.get('logo_height')} px"
                } if data_dict.get("logo_width") else None
            }}]
