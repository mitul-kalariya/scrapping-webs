"""Utility Function
"""
import os
import re
import json
import logging
from datetime import datetime

from crwddnews import exceptions
from crwddnews.constant import TODAYS_DATE, LOGGER


def create_log_file():
    """creating log file"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    """
    validating date range given for sitemap
    """
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
                "start_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as e:
        LOGGER.error("Error in __init__: %s", e, exc_info=True)
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
        return parsed_json
    except BaseException as exception:
        LOGGER.info("Error occured while getting parsed json %s", exception)
        raise exceptions.ArticleScrappingException(
            "Error occured while getting parsed json %s", exception
        ) from exception


def get_parsed_data(response):
    """generate required data as response json and response data

    Args:
        response (obj): site response object

    Returns:
        dict: returns 2 dictionary parsed_json and parsed_data
    """
    try:

        main_dict = {}
        topline = response.css("p.heading_small::text").get()
        main_dict["description"] = [topline]

        # title = response.css("h1.news_heading.detail_title::text").get()
        title = response.css("meta[name='title']::attr(content)").get()
        main_dict["title"] = [title]

        published_on = response.css("p.date::text").get()
        main_dict["published_at"] = [published_on]

        section = get_section(response)

        if section:
            main_dict["section"] = [section]
        display_text = response.css(
            "div.news_content p[class!='heading_small']::text"
        ).getall()

        if display_text:
            main_dict["text"] = [
                " ".join([re.sub("[\r\n\t]+", "", text).strip() for text in display_text])
            ]

        images = get_images(response)
        if images:
            main_dict["images"] = images

        thumbnail_image = get_thumbnail(response)
        if thumbnail_image:
            main_dict["thumbnail_image"] = [thumbnail_image]
        video = response.css(".views-field-field-video iframe::attr(src)").getall()
        if video:
            main_dict["embeded_video_url"] = video

        mapper = {"en": "English"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]
        return remove_empty_elements(main_dict)
    except BaseException as e:
        LOGGER.error("while scrapping parsed data %s", e)
        raise exceptions.ArticleScrappingException(f"while scrapping parsed data :{e}")


def get_thumbnail(response):
    """
    parsing a thumbnail url from the article
    returns : thumbnial
    """
    data = get_main(response)
    for data_block in data:
        if data_block.get("@type") == "WebPage":
            thumbnail = data_block.get("thumbnailUrl")
            if thumbnail:
                return thumbnail


def get_section(response):
    """
    parsing a section(breadcrumb)
    returns : breaedcrumb list
    """
    breadcrumb_list = response.css(
        "div.easy-breadcrumb a.easy-breadcrumb_segment-1::text"
    ).getall()
    if breadcrumb_list:
        return breadcrumb_list[-1]


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
        LOGGER.error("error parsing ld+json main data %s", e)
        raise exceptions.ArticleScrappingException(
            f"error parsing ld+json main data {e}"
        )


def get_images(response, parsed_json=False) -> list:
    """
    returns a images from the articles
    returns : Images
    """
    try:
        images = response.css("span.field-content img")
        pattern = r"[\r\n\t]"
        data = []
        for image in images:
            temp_dict = {}
            link = image.css("img::attr(src)").get()
            caption = image.css("img::attr(alt)").get()
            if parsed_json:
                if link:
                    temp_dict["@type"] = "ImageObject"
                    temp_dict["link"] = link
            else:
                if link:
                    temp_dict["link"] = link
                    if caption:
                        temp_dict["caption"] = re.sub(pattern, "", caption).strip()
            data.append(temp_dict)
        return data
    except BaseException as e:
        LOGGER.error("image fetching exception %s", e)
        raise exceptions.ArticleScrappingException(f"image fetching exception {e}")



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
    try:
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
    except BaseException as e:
        LOGGER.error("error while creating json file: %s", e)
        raise exceptions.ExportOutputFileException(
            f"error while creating json file: {e}"
        )
