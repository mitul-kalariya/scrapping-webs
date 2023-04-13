# Utility/helper functions
# utils.py

import os
import re
import json
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from crwbfmtv import exceptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from crwbfmtv.constant import TODAYS_DATE, LOGGER
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

pattern = r"[\r\n\t\"]+"

def validate_sitemap_date_range(start_date, end_date):
    start_date = (
        datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    )
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    try:
        if start_date and not end_date:
            raise exceptions.InvalidDateException(
                "end_date must be specified if start_date is provided"
            )
        if not start_date and end_date:
            raise exceptions.InvalidDateException(
                "start_date must be specified if end_date is provided"
            )

        if start_date and end_date and start_date > end_date:
            raise exceptions.InvalidDateException(
                "start_date should not be later than end_date"
            )

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "start_date should not be greater than today_date"
            )

        if start_date and end_date and end_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "end_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as e:
        LOGGER.error(f"Error in __init__: {e}", exc_info=True)
        raise exceptions.InvalidDateException(f"Error in __init__: {e}")


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists,
    empty dicts, or None elements from a dictionary.
    :param d: Input dictionary.
    :type d: dict
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


def get_raw_response(response):
    raw_resopnse = {
        "content_type": "text/html; charset=utf-8",
        "content": response.css("html").get(),
    }
    return raw_resopnse


def get_parsed_json(response):
    """
    extracts json data from web page and returns a dictionary
    Parameters:
        response(object): web page
    Returns
        parsed_json(dictionary): available json data
    """
    parsed_json = {}
    imageObjects = []
    videoObjects = []
    other_data = []
    ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
    for a_block in ld_json_data:
        data = json.loads(a_block)
        if data.get("@type") == "NewsArticle":
            parsed_json["main"] = data
        elif data.get("@type") in {"ImageGallery", "ImageObject"}:
            imageObjects.append(data)
        elif data.get("@type") == "VideoObject":
            videoObjects.append(data)
        else:
            other_data.append(data)

    parsed_json["imageObjects"] = imageObjects
    parsed_json["videoObjects"] = videoObjects
    parsed_json["other"] = other_data
    misc = get_misc(response)
    if misc:
        parsed_json["misc"] = misc

    return remove_empty_elements(parsed_json)


def get_main(response):
    """
    returns a list of main data available in the article from application/ld+json
    Parameters:
        response:
    Returns:
        main data
    """
    try:

        information = {}
        main = response.css('script[type="application/ld+json"]::text').getall()
        for block in main:
            data = json.loads(block)
            if data.get("@type") == "NewsArticle":
                information["article"] = data
            elif data.get("@type") == "WebPage":
                information["WebPage"] = data
            elif data.get("@type") == "VideoObject":
                information["VideoObject"] = data
            else:
                pass
        return information
    except BaseException as exception:
        LOGGER.error("Error while getting main %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error while getting main: {exception}"
        )


def get_misc(response):
    """
    returns a list of misc data available in the article from application/json
    Parameters:
        response:
    Returns:
        misc data
    """
    try:
        data = []
        misc = response.css('script[type="application/json"]::text').getall()
        for block in misc:
            data.append(json.loads(block))
        return data
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error while getting misc: {e}")


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
        "embed_video_link": None,
    }


def get_parsed_data(response):
    response_data = {}
    
    text = []
    main_json = get_main(response)
    article_json = main_json.get("article")
    videoobject_json = main_json.get("VideoObject")
    if article_json:
        main_json = article_json
    else:
        main_json = videoobject_json

    response_data = get_parsed_data_dict()
    article_title = response.css("h1.content_title::text").get()
    response_data["title"] = [re.sub(pattern, "", article_title).strip()]

    response_data |= get_dates_publisher(main_json, response)
    article_description = response.css("div.chapo::text").get()
    response_data["description"] = [article_description]

    article_text = " ".join(response.css("p::text").getall())
    text.append(re.sub(pattern, "", article_text).strip())

    article_blockquote_text = " ".join(response.css("span::text").getall())
    text.append(re.sub(pattern, "", article_blockquote_text))

    response_data["text"] = [" ".join(text)]

    response_data |= get_author(main_json,response)
    section = get_section(response)
    response_data["section"] = section

    # get thumbnail image and video url
    response_data |= get_thumbnail_image_video(main_json, response)

    article_images = get_images(response, response_data.get("thumbnail_image", None))
    response_data["images"] = article_images

    mapper = {"fr": "French"}
    article_lang = response.css("html::attr(lang)").get()
    response_data["source_language"] = [mapper.get(article_lang)]

    return remove_empty_elements(response_data)

def get_author(parsed_json_dict, response):
    if parsed_json_dict:
        return{
            "author": [parsed_json_dict.get("author",None)]
        }
    elif response.css("span.author_name::text"):
        article_author = response.css("span.author_name::text").get() or None
        if article_author:
            return {"author":[
                {"@type": "Person", "name": re.sub(pattern, "", article_author).strip()}
            ]}
    else:
        return {"author":None}


def get_images(response, thumbnail_image) -> list:
    """
    Extracts all the images present in the web page.
    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    data = []
    if response.css("figure"):
        for i in response.css("figure"):
            image = i.css("figure img::attr(src)").get()
            caption = i.css("figcaption span::text").get()
            if thumbnail_image and image not in thumbnail_image:
                data.append(
                    {
                        "link": image,
                        "caption": caption or None,
                    }
                )
            else:
                 data.append(
                    {
                        "link": image,
                        "caption": caption or None,
                    }
                )
    return data


def get_dates_publisher(parsed_json_dict, response):
    if parsed_json_dict:
        return {
            "published_at": [parsed_json_dict.get("datePublished")]
            or [parsed_json_dict.get("uploadDate")],
            "modified_at": [parsed_json_dict.get("dateModified")],
            "publisher": [parsed_json_dict.get("publisher")],
        }
    else:
        return {
            "published_at": [response.css("div.content_datetime time::text").get()],
        }


def get_thumbnail_image_video(parsed_json_dict, response):
    if parsed_json_dict:
        thumbnail_image = []
        video_links = []
        article_thumbnail = parsed_json_dict.get("image", None)
        if article_thumbnail:
            thumbnail_image.append(article_thumbnail.get("contentUrl",None))
        thumbnail_video = parsed_json_dict.get("video")
        if thumbnail_video:
            video_links.append(thumbnail_video.get("embedUrl",None))
    
        return format_dictionary(
            {
                "thumbnail_image": parsed_json_dict.get("thumbnailUrl", None)
                or thumbnail_image,
                "embed_video_link": parsed_json_dict.get("embedUrl", None)
                or video_links,
            }
        )
    else:
        return {"thumbnail_image": None, "embed_video_link": None}


def get_section(response) -> list:
    breadcrumb_list = response.xpath("//ul[@class='list_inbl']//li[2]//a//span/text()")
    if breadcrumb_list:
        for i in breadcrumb_list:
            return [i.extract()]


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
        filename = f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)
    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)


def format_dictionary(raw_dictionary):
    """Formatting dictionary with all the values converted to list

    Args:
        raw_dictionary (dict)

    Returns:
        dict: formatted dictionary
    """
    for key, value in raw_dictionary.items():
        if not isinstance(value, list):
            raw_dictionary[key] = [value]
    return raw_dictionary
