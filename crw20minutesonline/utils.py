""" General functions """
from datetime import timedelta, datetime
import json

from bs4 import BeautifulSoup
from scrapy.loader import ItemLoader

from crw20minutesonline.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)

from crw20minutesonline.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)

ERROR_MESSAGES = {
    "InputMissingException": "'{}' field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}
language_mapper = {"en": "English", "fr": "French"}

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


def date_in_date_range(published_date, date_range_lst):
    """
    return true if date is in given start date and end date range
    """
    return published_date.date() in date_range_lst


def validate_arg(param_name, param_value, custom_msg="") -> None:
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
        "Other": [],
        "misc": [],
    }
    for block in blocks:
        if "LiveBlogPosting" in json.loads(block).get(
            "@type", [{}]
        ) or "NewsArticle" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(block)
        elif "ImageGallery" in json.loads(block).get(
            "@type", [{}]
        ) or "ImageObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["imageObjects"].append(json.loads(block))
        elif "VideoObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["videoObjects"].append(json.loads(block))
        else:
            parsed_json_flter_dict["Other"].append(json.loads(block))
    parsed_json_flter_dict["misc"] = [json.loads(data) for data in misc]
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


def get_parsed_data(response: str, parsed_json_main: list, video_object: dict) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_data_dict = get_parsed_data_dict()

    parsed_data_dict |= {
        "source_country": ["France"],
        "source_language": [
            language_mapper.get(response.css("html::attr(lang)").get(), None)
        ],
    }
    parsed_data_dict |= get_author_details(parsed_json_main, response)
    parsed_data_dict |= get_descriptions_date_details(parsed_json_main)
    parsed_data_dict |= get_publihser_details(parsed_json_main)
    parsed_data_dict |= get_text_title_section_details(parsed_json_main, response)
    parsed_data_dict |= get_thumbnail_image_video(video_object, response)
    parsed_data_dict |= {"time_parsed": [str(datetime.now())]}
    return remove_empty_elements(parsed_data_dict)


def get_author_details(parsed_data: list, response: str) -> dict:
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json data
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
            {"name": response.css("#detailContent > div.byline > div::text").get()}
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


def get_descriptions_date_details(parsed_data: list) -> dict:
    """
    Returns description, modified date, published date details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: description, modified date, published date related details
    """
    article_data = {
        "description": None,
        "modified_at": None,
        "published_at": None,
    }
    if "NewsArticle" in parsed_data.get(
        "@type"
    ) or "LiveBlogPosting" in parsed_data.get("@type"):
        article_data |= {
            "description": [parsed_data.get("description")],
            "modified_at": [parsed_data.get("dateModified")],
            "published_at": [parsed_data.get("datePublished")],
        }
    return article_data


def get_publihser_details(parsed_data: list) -> dict:
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
                "name": publisher.get("name"),
                "logo": {
                    "url": parsed_data.get("publisher").get("logo").get("url"),
                    "width": str(parsed_data.get("publisher").get("logo").get("width"))
                    + " px",
                    "height": str(
                        parsed_data.get("publisher").get("logo").get("height")
                    )
                    + " px",
                },
            }
            for publisher in [parsed_data.get("publisher")]
        )
    return {"publisher": publisher_details}


def get_text_title_section_details(parsed_data: list, response: str) -> dict:
    """
    Returns text, title, section details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: text, title, section details
    """
    soup = BeautifulSoup(response.body, "html.parser")
    content_div = soup.find("div", class_="content")
    text = ""
    class_names = ["sharebar", "tags", "box", "enclose", "toolbar", "media-caption"]
    for class_name in class_names:
        for elem in content_div.find_all(class_=class_name):
            elem.decompose()

    for elem in content_div.find_all("script"):
        elem.decompose()

    text = content_div.get_text(strip=True)

    return {
        "title": [parsed_data.get("headline")],
        "text": [text],
        "section": [parsed_data.get("articleSection")],
        "tags": parsed_data.get("keywords", []),
    }


def get_thumbnail_image_video(video_object: dict, response: str) -> dict:
    """
    Returns thumbnail images, images and video details
    Args: video_object: response of VideoObject data
    parsed_data: response of application/ld+json data
    Returns: dict: thumbnail images, images and video details
    """

    video = None
    description = None
    images = []
    if len(video_object[0]) > 0:
        # breakpoint()
        for videos in video_object:
            if video_url := videos.get("embedUrl"):
                video = video_url
            description = videos.get("description")
    else:
        video = response.selector.css("iframe.digitekaPlayer::attr('src')").getall()

    for figure in response.css("article div.content figure"):
        caption_text = ""
        for caption_part in figure.css("figcaption *::text").getall():
            caption_text += caption_part.strip()
        if link := figure.css("img::attr(src)").get():
            images.append(
                {
                    "link": link,
                    "caption": caption_text if caption_text else None,
                }
            )
    thumbnail_image_url = response.css(
        "meta[property='og:image']::attr(content)"
    ).getall()

    return {
        "thumbnail_image": thumbnail_image_url,
        "images": images,
        "video": [{"link": video, "caption": description}],
    }
