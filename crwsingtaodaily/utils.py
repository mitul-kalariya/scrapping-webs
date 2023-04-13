"""Utility Functions"""
import os
import json
import logging
import re
from datetime import datetime
from crwsingtaodaily import exceptions
from crwsingtaodaily.constant import LOGGER


def get_raw_response(response):
    """parsing raw response
    returns: raw response
    """
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
    try:
        parsed_json = {}
        image_objects = []
        video_objects = []
        other_data = []
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
        for a_block in ld_json_data:
            data = json.loads(a_block)
            if data.get("@type") == "Article":
                parsed_json["main"] = data
            elif data.get("@type") in {"ImageGallery", "ImageObject"}:
                image_objects.append(data)
            elif data.get("@type") == "VideoObject":
                video_objects.append(data)
            else:
                other_data.append(data)

        parsed_json["imageObjects"] = image_objects
        parsed_json["videoObjects"] = video_objects
        parsed_json["other"] = other_data
        misc = get_misc(response)
        if misc:
            parsed_json["misc"] = misc
        return remove_empty_elements(parsed_json)

    except BaseException as exception:
        LOGGER.info("Error occured while getting parsed json %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error occurred while getting parsed json {exception}"
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
    except BaseException as exception:
        LOGGER.error("error while getting misc: %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error while getting misc: {exception}"
        )


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


def get_parsed_data(response: str) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """

    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= get_country_language_details()
    parsed_data_dict |= get_author_details(response)
    parsed_data_dict |= get_descriptions_date_details(response)
    parsed_data_dict |= get_publisher_details(response)
    parsed_data_dict |= get_text_title_section_tag_details(response)
    parsed_data_dict |= get_thumbnail_image_video(response)
    final_dict = format_dictionary(parsed_data_dict)
    return remove_empty_elements(final_dict)


def get_country_language_details() -> dict:
    """
    Return country related details

    Returns:
        dict: country related details
    """

    return {"source_country": ["China"], "source_language": ["Chinese"]}


def get_author_details(response: str) -> dict:
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: author related details
    """
    author_details = response.css('meta[name="author"]::attr(content)').getall()
    return {"author": {"name": author_details}}


def get_descriptions_date_details(response: list) -> dict:
    """
    Returns description, modified date, published date details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: description, modified date, published date related details
    """
    data_dict = {}
    if response.css('meta[name="description"]').get():
        data_dict["description"] = response.css(
            'meta[name="description"]::attr(content)'
        ).get()
    pub_date = response.css("header span.date::text").get()
    data_dict["published_at"] = pub_date

    return data_dict


def get_publisher_details(response) -> dict:
    """
    Returns publisher details like name, type, id
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: publisher details like name, type, id related details
    """
    publisher = response.css('meta[name="publisher"]::attr(content)').get()
    if publisher:
        return {"publisher": {"name": publisher}, "publisher_name": publisher}
    return {"publisher": None}


def get_text_title_section_tag_details(response: str) -> dict:
    """
    Returns text, title, section details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: text, title, section, tag details
    """
    return {
        "title": response.css("header > h1::text").getall(),
        "text": [
            re.sub(r"[\r\t\n]", "", " ".join(response.css("p::text").getall())).strip()
        ],
        "tags": response.css(
            '.sb-body div form input[type="submit"]::attr(title)'
        ).getall(),
    }


def get_thumbnail_image_video(response: str) -> dict:
    """
    Returns thumbnail images, images and video details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: thumbnail images, images and video details
    """
    thumbnail_url = []
    images_list = []
    video = []
    thumbnail = response.css('article[class ="content"] figure img::attr(src)').get()
    if thumbnail:
        thumbnail_url.append(thumbnail)
    images = response.css('article[class="align-center"]')
    for image in images:
        url = image.css("div div img::attr(src)").get()
        caption = image.css("div div.media-library-item__name::text").get()
        images_list.append(
            {"link": url, "caption": re.sub(r"[\r\t\n]", "", caption).strip()}
        )
    video_url = response.css(".video-js source::attr(src)").get()
    video.append({"link": video_url})
    return remove_empty_elements(
        {"images": images_list, "thumbnail_image": thumbnail_url, "video": video}
    )


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


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
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


def create_log_file():
    """creating log file"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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
        json.dump(file_data, file, indent=4, ensure_ascii=False)
