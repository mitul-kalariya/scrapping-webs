# Utility/helper functions
# utils.py

import os
import re
import json
import logging
from datetime import datetime
from crwntv import exceptions
from crwntv.constant import TODAYS_DATE, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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
    """
    extracts json data from web page and returns a dictionary
    Parameters:
        response(object): web page
    Returns
        parsed_json(dictionary): available json data
    """
    parsed_json = {}
    other_data = []
    ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
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
    response_data = {}
    pattern = r"[\r\n\t\"]+"

    article_title = response.css("h2 span.article__headline::text").get()
    response_data["title"] = [re.sub(pattern, "", article_title).strip()]

    article_author = get_main(response)
    response_data['author'] = article_author[0].get('author')

    article_published = response.css("span.article__date::text").get()
    response_data["published_at"] = [article_published]

    article_modified = response.css('meta[name="last-modified"]::attr(content)').get()
    response_data["modified_at"] = [article_modified]

    article_description = response.css("p strong::text").get()
    response_data["description"] = [article_description]

    article_publisher = get_main(response)
    response_data["publisher"] = [article_publisher[0].get("publisher")]

    article_text = " ".join(response.css("p::text").getall())
    if article_text:
        response_data["text"] = [article_text]
    elif response.css("div.article__text::text").get():
        response_data["text"] = [
            re.sub(pattern, "", response.css("div.article__text::text").get()).strip()
        ]

    article_thumbnail = get_thumbnail(response)
    response_data["thumbnail_image"] = article_thumbnail

    article_video = response.css("div.vplayer__video div video source::attr(src)").get()
    link = re.findall(r"http?.*?\.mp4", str(article_video))
    response_data["embed_video_link"] = link

    article_tags = response.css("section.article__tags ul li a::text").getall()
    response_data["tags"] = article_tags
    mapper = {"de": "German"}
    article_lang = response.css("html::attr(lang)").get()
    response_data["source_language"] = [mapper.get(article_lang)]

    return remove_empty_elements(response_data)


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
        raise exceptions.ArticleScrappingException(f"Error while getting main: {e}")


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
        raise exceptions.ArticleScrappingException(f"Error while getting misc: {e}")


def get_thumbnail(response) -> list:
    """extract thumbnail info from article

    Returns:
        list: target_data
    """
    video_article = response.css("div.vplayer div.vplayer__video")
    normal_article = response.css("div.article__media figure")
    data = []
    if normal_article:
        for i in normal_article:
            thumbnail_image = i.css("picture img::attr(src)").get()
            if thumbnail_image:
                data.append(thumbnail_image)
    elif video_article:
        for j in video_article:
            thumbnail_image = j.css("img::attr(src)").get()
            if thumbnail_image:
                data.append(thumbnail_image)
    return data


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
