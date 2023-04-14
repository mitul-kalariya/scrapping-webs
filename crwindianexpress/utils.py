""" General functions """
from datetime import timedelta, datetime
import itertools
import json
import re
from w3lib.html import remove_tags


from scrapy.loader import ItemLoader

from crwindianexpress.items import (
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

SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"
language_mapper = {"en": "English"}


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
        validate_arg(
            InvalidDateException,
            scrape_start_date <= datetime.now().date()
            and scrape_end_date <= datetime.now().date(),
        )
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
        "imageObjects": [],
        "videoObjects": [],
        "other": [],
        "misc": [],
    }
    for block in blocks:
        if "NewsArticle" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(block)
        elif (
            "ImageGallery" in json.loads(block).get("@type", [{}])
            or "imageGallery" in json.loads(block).get("@type", [{}])
            or "ImageObject" in json.loads(block).get("@type", [{}])
        ):
            parsed_json_flter_dict["imageObjects"].append(json.loads(block))
        elif "VideoObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["videoObjects"].append(json.loads(block))
        else:
            parsed_json_flter_dict["other"].append(json.loads(block))
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

    return remove_empty_elements(dict(article_raw_parsed_json_loader.load_item()))


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


def get_parsed_data(
    response: str,
    parsed_json_main: list,
    parsed_json_images: list,
    parsed_json_videos: list,
    article_url: str,
) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld main data
        parsed_json_images: A list of dictionary with applications/+ld iamges data
        parsed_json_videos: A list of dictionary with applications/+ld videos data
        article_url: article url
    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_data_dict = get_parsed_data_dict()

    parsed_data_dict |= get_country_details()
    parsed_data_dict |= get_language_details(response)
    parsed_data_dict |= get_author_details(parsed_json_main, response)
    parsed_data_dict |= get_descriptions_date_details(
        parsed_json_main, response, article_url
    )
    parsed_data_dict |= get_publihser_details(parsed_json_main, response)
    parsed_data_dict |= get_text_title_section_details(
        parsed_json_main, response, article_url
    )
    parsed_data_dict |= get_thumbnail_image_video(
        response,
        article_url,
        parsed_json_images,
        parsed_json_videos,
    )
    parsed_data_dict |= {"time_parsed": [str(datetime.now())]}

    return remove_empty_elements(parsed_data_dict)


def get_country_details() -> dict:
    """
    Return country related details

    Returns:
        dict: country related details
    """
    return {"source_country": ["India"]}


def get_language_details(response: str) -> dict:
    """
    Return language related details
    Args:
        response: provided response
    Returns:
        dict: language related details
    """
    return {
        "source_language": [
            language_mapper.get(response.css("html::attr(lang)").get(), None)
        ]
    }


def get_author_details(parsed_data: list, response: str) -> dict:
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json main data
        response: provided response
    Returns:
        dict: author related details
    """
    author_details = []
    author_data = (
        parsed_data.get("author")
        if isinstance(parsed_data.get("author"), list)
        else [parsed_data.get("author")]
    )

    if not parsed_data.get("author"):
        return author_details.append(
            {
                "name": response.css("#storycenterbyline>div>a::text").get(),
                "url": response.css("#storycenterbyline>div>a::attr(href)").get(),
            }
        )
    author_details.extend(
        {
            "@type": author.get("@type"),
            "name": author.get("name"),
            "url": author.get("url", None),
        }
        for author in author_data
    )
    return {"author": author_details}


def get_descriptions_date_details(
    parsed_data: list, response: str, article_url: str
) -> dict:
    """
    Returns description, modified date, published date details
    Args:
        parsed_data: response of application/ld+json main data
    Returns:
        dict: description, modified date, published date related details
    """

    description = []
    modified_at = []
    published_at = []

    if "/videos/" in article_url:
        description = [response.css("meta[name^=description]::attr(content)").get()]
        published_at = [
            response.css(
                "meta[property^='article:published_time']::attr(content)"
            ).get()
        ]
        modified_at = [
            response.css("meta[property^='article:modified_time']::attr(content)").get()
        ]
    elif "/photos/" in article_url:
        description = [response.css("meta[name^=description]::attr(content)").get()]
        modified_at = [parsed_data.get("dateModified")]
        published_at = [parsed_data.get("datePublished")]
    elif "NewsArticle" in parsed_data.get("@type"):
        description = [parsed_data.get("description")]
        modified_at = [parsed_data.get("dateModified")]
        published_at = [parsed_data.get("datePublished")]
    else:
        description = response.css("h2.synopsis::text").getall()
        modified_at = (
            response.css("div.editor-date-logo div span::text").getall()
            or response.css("span.updated-date::attr(content)").getall()
        )
        published_at = response.css("div.ie-first-publish span::text").getall()

    return {
        "description": description,
        "modified_at": modified_at,
        "published_at": published_at,
    }


def get_publihser_details(parsed_data: list, response: str) -> dict:
    """
    Returns publisher details like name, type, id
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: publisher details like name, type, id related details
    """

    publisher_details = []
    if parsed_data.get("publisher"):
        publisher_details.extend(
            {
                "@id": publisher.get("@id"),
                "@type": publisher.get("@type"),
                "name": response.css(
                    "#wrapper div.main-header__logo img::attr(title)"
                ).get(),
                "logo": {
                    "type": "ImageObject",
                    "url": response.css(
                        "#wrapper div.main-header__logo img::attr(src)"
                    ).get(),
                    "width": {
                        "type": "Distance",
                        "name": response.css(
                            "#wrapper div.main-header__logo img::attr(width)"
                        ).get()
                        + "px",
                    },
                    "height": {
                        "type": "Distance",
                        "name": response.css(
                            "#wrapper div.main-header__logo img::attr(height)"
                        ).get()
                        + "px",
                    },
                },
            }
            for publisher in [parsed_data.get("publisher")]
        )
    return {"publisher": publisher_details}


def get_text_title_section_details(
    parsed_data: list, response: str, article_url: str
) -> dict:
    """
    Returns text, title, section details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
        article_url: url of article
    Returns:
        dict: text, title, section details
    """
    section = None
    tag = None
    if "/photos/" in article_url:
        section = response.css(".m-breadcrumb>li *::text").getall()
        section = section[-1] if len(section) > 1 else section
        tag = "".join(
            response.css("meta[name=news_keywords]::attr(content)").getall()
        ).split(",")
    elif "/videos/" in article_url:
        tag = "".join(
            response.css("meta[name=news_keywords]::attr(content)").getall()
        ).split(",")
    return {
        "title": [parsed_data.get("headline")],
        "text": ["".join(parsed_data.get("articleBody", []))],
        "section": [section or parsed_data.get("articleSection")],
        "tags": tag or parsed_data.get("keywords"),
    }


def remove_tags_spaces(article_text: list) -> list:
    """
    Returns formatted article caption
    Args:
        article_url: article url
    Returns:
        list: formatted article caption
    """
    return [
        re.sub(SPACE_REMOVER_PATTERN, "", remove_tags(single_text.strip()))
        for single_text in article_text
    ]


def get_thumbnail_image_video(
    response: str,
    article_url: str,
    parsed_json_images: str,
    parsed_json_videos: str,
) -> dict:
    """
    Returns thumbnail images, images and video details
    Args:
        article_url: article url
        parsed_json_images: response of application/ld+json iamges data
        parsed_json_videos: response of application/ld+jsonvideos data
        response: provided response
    Returns:
        dict: thumbnail images, images and video details
    """
    images = []
    caption = []
    videos = []

    if "/photos/" in article_url:
        caption = remove_tags_spaces(
            response.css(".caption-summary>p:first-of-type").getall()
        )

        for img in parsed_json_images:
            images = img.get("image", {}).get("url", [])

    elif "/videos/" in article_url:
        for video in parsed_json_videos:
            videos = video.get("contentUrl", [])
    else:
        for img, cap in itertools.zip_longest(
            response.css("span.custom-caption > img::attr(src)").getall(),
            remove_tags_spaces(response.css("span.custom-caption").getall()),
            fillvalue=None,
        ):
            images.append(img)
            caption.append(cap)
        videos = response.css("span.embed-youtube iframe::attr(src)").getall()
        for video in response.css("span.embed-youtube iframe::attr(src)").getall():
            videos = video

    return {
        "images": [
            {"link": img, "caption": cap}
            for img, cap in itertools.zip_longest(images, caption)
        ],
        "video": [
            {
                "link": videos,
            }
        ],
        "thumbnail_image": response.css(
            "meta[property='og:image']::attr(content)"
        ).getall(),
    }
