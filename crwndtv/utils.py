# Utility/helper functions
# utils.py

import os
import re
import json
import time
import logging
from datetime import datetime

from crwndtv import exceptions
from crwndtv.constant import TODAYS_DATE, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
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

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "start_date should not be greater than today_date"
            )

        if start_date and end_date and end_date > TODAYS_DATE:
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
        "content_type": "text/html; charset=UTF-8",
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
        ld_json_data = response.css('script:contains("description")::text').get()
        parsed_json["main"] = json.loads(ld_json_data)

        return remove_empty_elements(parsed_json)
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed json {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting parsed json {exception}"
        ) from exception


def get_parsed_data(response):
    """generate required data as response json and response data

    Args:
        response (obj): site response object

    Returns:
        dict: returns 2 dictionary parsed_json and parsed_data
    """
    try:
        pattern = r"[\r\n\t\</h2>\<h2>]+"
        main_dict = {}
        main_data = json.loads(
            response.css('script:contains("description")::text').get()
        )

        main_dict["description"] = [main_data["description"]]

        title = response.css("div.sp-ttl-wrp h1::text").get()
        if title:
            title = re.sub(r"[\n\t\r\"]", "", title).strip()
            main_dict["title"] = [title]

        published_on = response.css("meta[name='publish-date']::attr(content)").get()
        main_dict["published_at"] = [published_on]

        modified_on = response.css(
            ".pst-by_ul span.pst-by_lnk span[itemprop]::attr(content)"
        ).get()
        main_dict["modified_at"] = [modified_on]

        author = get_author(response)
        if author:
            main_dict["author"] = [author]

        section = response.css(
            'span.brd-nv_li.current span[itemprop="name"]::text'
        ).get()
        if section:
            main_dict["section"] = [section]

        publisher = main_data["publisher"]
        main_dict["publisher"] = [publisher]

        display_text = get_content(response)
        main_dict["text"] = display_text

        tags = [main_data["keywords"]]
        main_dict["tags"] = tags

        thumbnail_image = response.css("#story_image_main::attr(src)").get()
        if thumbnail_image:
            main_dict["thumbnail_image"] = [thumbnail_image]

        source_language = "English"
        main_dict["source_language"] = [source_language]

        video = response.css('meta[itemprop="ContentUrl"]::attr(content)').get()
        main_dict["embed_video_link"] = video
        return remove_empty_elements(main_dict)
    except BaseException as e:
        LOGGER.error(f"while scrapping parsed data {e}")
        raise exceptions.ArticleScrappingException(f"while scrapping parsed data :{e}")


def get_author(response):
    author = {}
    author_name = response.css("div.pst-by_ul span[itemprop='name']::text").get()
    author_url = response.css(".pst-by_li a[class!='pst-by_lnk']::attr(href)").get()
    author["name"] = author_name
    author["url"] = author_url

    return author


def get_content(response):
    pattern = r"[\n\t\r\"]"
    article_content = response.css(
        "div.sp-cn.ins_storybody p[class!='ins_instory_dv_caption sp_b']::text"
    ).getall()
    description = " ".join(article_content)
    return [re.sub(pattern, "", description).strip()]


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
        LOGGER.error(f"error while creating json file: {e}")
        raise exceptions.ExportOutputFileException(
            f"error while creating json file: {e}"
        )
