# Utility/helper functions
# utils.py

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_date_range(start_date, end_date):
    """
    return range of all date between given date
    if not end_date then take start_date as end date
    """
    try:
        date_range_lst = []
        if start_date is None and end_date is None:
            start_date = (
                end_date
            ) = datetime.now().date()

        for n in range(int((end_date - start_date).days) + 1):
            date_range_lst.append(start_date + timedelta(n))
        return date_range_lst
    except Exception as exception:
        logger.log(
            msg="Error occurred while generating date range. " + str(exception),
            level=logging.ERROR,
        )
        return []


def validate(type=None, url=None, start_date=None, end_date=None):
    """
        This function to validate the input args
        like start_Date, end_date, type and raise error if require else return nothing
        This should be called from __init__ method of Spider
    """
    error_msg_dict = {}
    if type not in ['sitemap', 'article']:
        error_msg_dict["error_msg"] = "Invalid type argument. Must be 'sitemap' or 'article'."
    if type == "sitemap":
        if url:
            error_msg_dict["error_msg"] = "Invalid argument. url is not required for sitemap."

        if start_date and end_date:
            if start_date > end_date:
                error_msg_dict["error_msg"] = "Please enter valid date range."
            elif int((end_date - start_date).days) > 30:
                error_msg_dict["error_msg"] = "Please enter date range between 30 days"

    elif type == "article":
        if not url:
            error_msg_dict["error_msg"] = "Argument url is required for type article."
        if start_date or end_date:
            error_msg_dict[
                "error_msg"] = "Invalid argument. start_date and end_date argument is not required for article."

    return error_msg_dict


def get_raw_response(response):
    """
        This function should return the raw response object
    """
    return {
        "content_type": response.headers.get("Content-Type").decode("utf-8"),
        "content": response.text,
    }


def get_parsed_json(response):
    """
        This function should return the parsed json object
    """
    return {
        "main": [json.loads(block) for block in response.css('script[type="application/ld+json"]::text').getall()],
    }


def get_parsed_data(response):
    """
        This function should return the parsed data object
    """
    block = [json.loads(block) for block in response.css('script[type="application/ld+json"]::text').getall()][0]
    return remove_empty_keys({
        "author": [{"@type": get_author_type(block),
                    "name": get_author(block)}],
        "description": [get_description(block)],
        "published_at": [get_published_at(block)],
        "modified_at": [get_modified_at(block)],
        "publisher": [
            {
                "@id": get_publisher_id(block),
                "@type": get_publisher_type(block),
                "name": get_publisher_name(block),
                "logo": {
                    "type": get_logo_type(block),
                    "url": get_logo_url(block),
                    "width": get_logo_width(block),
                    "height": get_logo_height(block),
                },
            }
        ],
        "text": get_text(response),
        "title": [get_title(block)],
        "images": [{"link": get_image_url(block), "caption": get_image_caption(block)}],
    })


# below method should be called from get_parsed_data function


def get_author_type(response):
    if response.get("author"):
        return response.get("author")[0].get("@type")
    return None


def get_author(response):
    if response.get("author"):
        return response.get("author")[0].get("name")
    return None


def get_description(response):
    return response.get("description", None)


def get_publisher(response):
    pass


def get_modified_at(response):
    return response.get("dateModified")


def get_published_at(response):
    return response.get("datePublished")


def get_publisher_id(response):
    if response.get("publisher"):
        return response.get("publisher").get("@id")
    return None


def get_publisher_type(response):
    if response.get("publisher"):
        return response.get("publisher").get("@type")
    return None


def get_publisher_name(response):
    if response.get("publisher"):
        return response.get("publisher").get("name")
    return None


def get_logo_type(response):
    if response.get("logo"):
        return response.get("logo").get("@type")
    return None


def get_logo_url(response):
    if response.get("logo"):
        return response.get("logo").get("url")
    return None


def get_logo_width(response):
    if response.get("logo") and response.get("logo").get("width"):
        return {
            "type": "Distance",
            "name": f"{response.get('logo').get('width')} px"
        }
    return None


def get_logo_height(response):
    if response.get("logo") and response.get("logo").get("height"):
        return {
            "type": "Distance",
            "name": f"{response.get('logo').get('height')} px",
        }
    return None


def get_text(response):
    text_list = response.css("p.c-article-body__text::text").getall()
    return "".join(text_list)


def get_image_url(response):
    return response.get("image", {}).get("url")


def get_image_caption(response):
    return response.get("image", {}).get("description")


def get_title(response):
    return response.get("headline")


def remove_empty_keys(obj):
    """
    Remove all keys and parent keys if all child keys are blank or None.

    Args:
        obj (dict): The object to remove empty keys from.

    Returns:
        dict: The modified object with empty keys removed.
    """
    if isinstance(obj, dict):
        return {k: remove_empty_keys(v) for k, v in obj.items() if v and remove_empty_keys(v)}
    elif isinstance(obj, (list, tuple)):
        return [remove_empty_keys(item) for item in obj if item and remove_empty_keys(item)]
    else:
        return obj
