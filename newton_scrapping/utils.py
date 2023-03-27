# Utility/helper functions
# utils.py

import os
import re
import json
import logging
from datetime import datetime
from newton_scrapping import exceptions
from newton_scrapping.constants import TODAYS_DATE, BASE_URL, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()  if end_date else None
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

        if start_date and end_date and start_date == end_date:
            raise exceptions.InvalidDateException(
                "start_date and end_date must not be the same"
            )

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "start_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as e:
        LOGGER.error(f"Error in __init__: {e}", exc_info=True)
        raise exceptions.InvalidDateException(f"Error in __init__: {e}")


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


def get_raw_response(response):
    raw_resopnse = {
        "content_type": "text/html; charset=utf-8",
        "content": response.css("html").get(),
    }
    return raw_resopnse


def get_parsed_json(response):
    parsed_json = {}
    main = get_main(response)
    if main:
        parsed_json["main"] = main
    misc = get_misc(response)
    if misc:
        parsed_json["misc"] = misc

    return parsed_json


def get_parsed_data(response):

    pattern = r"[\r\n\t\"]+"
    main_dict = {}

    # extract author info
    authors = get_author(response.css("div.copytext-element-wrapper"))
    main_dict["author"] = authors

    # extract main headline of article
    title = response.css("span.seitenkopf__headline--text::text").get()
    main_dict["title"] = [title]

    publisher = get_main(response)
    main_dict["publisher"] = [publisher[0].get("publisher")]

    # extract the date published at
    published_at = response.css("div.metatextline::text").get()
    clean_time = re.sub(pattern, "", published_at).strip()
    main_dict["published_at"] = [clean_time]

    descryption = response.css("p strong::text").get()
    main_dict["description"] = [re.sub(pattern, "", descryption).strip()]

    # extract the description or read text of the article
    text = response.css("p.textabsatz::text").getall()
    text = [re.sub(pattern, "", i) for i in text]
    main_dict["text"] = [" ".join(list(filter(None, text)))]

    # extract the thumbnail image
    thumbnail_image = response.css(
        "picture.ts-picture--topbanner .ts-image::attr(src)"
    ).get()
    main_dict["thumbnail_image"] = [BASE_URL + thumbnail_image]

    # extract video files if any
    video = get_embed_video_link(response.css("div.copytext__video"))
    main_dict["embed_video_link"] = video

    # extract tags associated with article
    tags = response.css("ul.taglist li a::text").getall()
    main_dict["tags"] = tags

    article_lang = response.css("html::attr(lang)").get()
    main_dict["language"] = [article_lang]

    return remove_empty_elements(main_dict)


def get_main(response):
    """
    returns a list of main data available in the article from application/ld+json
    Parameters:
        response:
    Returns:
        main data
    """
    try:
        data = []
        misc = response.css('script[type="application/ld+json"]::text').getall()
        for block in misc:
            data.append(json.loads(block))
        return data
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error while getting main: {e}")


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


def get_author(response) -> list:
    info = []
    if response:
        for child in response:
            a_dict = {}
            auth_name = child.css("span.id-card__name::text").get()
            if auth_name:
                a_dict["@type"] = "Person"
                a_dict["name"] = auth_name.strip()
                link = child.css("a.id-card__twitter-id::attr(href)").get()
                if link:
                    a_dict["url"] = link
                info.append(a_dict)

        return info


def get_embed_video_link(response) -> list:
    info = []
    for child in response:
        video = child.css("div.ts-mediaplayer::attr(data-config)").get()
        if video:
            video_link = re.findall(r"http?.*?\.mp4", video)[0]
            if video_link:
                info.append(video_link)
    return info


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
