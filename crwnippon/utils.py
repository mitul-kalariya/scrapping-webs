# Utility/helper functions
# utils.py

import os
import re
import json
import logging
from datetime import datetime
from crwnippon import exceptions
from crwnippon.constant import TODAYS_DATE, BASE_URL, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(since, until):
    since = (
        datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
    )
    until = datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
    try:
        if (since and not until) or (not since and until):
            raise exceptions.InvalidDateException(
                "since or until must be specified"
            )

        if since and until and since > until:
            raise exceptions.InvalidDateException(
                "since should not be later than until"
            )

        if since > TODAYS_DATE or until > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "since and until should not be greater than today_date"
            )

        if since and until and since > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "since should not be greater than today_date"
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
    """
    extracts json data from web page and returns a dictionary
    Parameters:
        response(object): web page
    Returns
        parsed_json(dictionary): available json data
    """
    parsed_json = {}
    other_data = []
    ld_json_data = response.css(
        'script[type="application/ld+json"]::text').getall()
    for a_block in ld_json_data:
        data = json.loads(a_block)
        if data.get("@type") == "NewsArticle":
            parsed_json["main"] = data
        elif data.get("@type") == "ImageGallery":
            parsed_json["ImageGallery"] = data
        elif data.get("@type") == "VideoObject":
            parsed_json["VideoObject"] = data
        else:
            other_data.append(data)

    parsed_json["Other"] = other_data
    misc = get_misc(response)
    if misc:
        parsed_json["misc"] = misc

    return remove_empty_elements(parsed_json)


def get_parsed_data(response):

    pattern = r"[\r\n\t\"]+"
    main_dict = {}
    video = []
    main_data = get_main(response)

    # extract author info
    authors = [main_data[0].get("author")]
    main_dict["author"] = authors

    # extract main headline of article
    title = response.css("span.seitenkopf__headline--text::text").get()
    main_dict["title"] = [title]

    main_dict["publisher"] = [main_data[0].get("publisher")]

    # extract the date published at
    main_dict["published_at"] = [main_data[0].get("datePublished")]
    main_dict["modified_at"] = [main_data[0].get("dateModified")]
    main_dict["description"] = [main_data[0].get("description")]

    # extract the description or read text of the article
    text = response.css("p.textabsatz::text").getall()
    text = [re.sub(pattern, "", i) for i in text]
    if text:
        main_dict['text'] = ["".join(list(filter(None, text)))]

    # extract the thumbnail image
    thumbnail_image = response.css(
        "picture.ts-picture--topbanner .ts-image::attr(src)"
    ).get()
    if thumbnail_image:
        main_dict["thumbnail_image"] = [BASE_URL + thumbnail_image]

    # extract video files if any
    frame_video = get_embed_video_link(response.css("div.copytext__video"))
    if frame_video:
        video.extend(frame_video)

    main_dict["embed_video_link"] = video

    # extract tags associated with article
    tags = response.css("ul.taglist li a::text").getall()
    main_dict["tags"] = tags

    mapper = {'de': "German"}
    article_lang = response.css("html::attr(lang)").get()
    main_dict["source_language"] = [mapper.get(article_lang)]

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
        json.dump(file_data, file, indent=4, ensure_ascii = False)