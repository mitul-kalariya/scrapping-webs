"""Utility/helper functions"""
# utils.py

import os
import re
import json
import logging
from datetime import datetime, timedelta
from w3lib.html import remove_tags
from crwskytg24 import exceptions
from crwskytg24.constant import TODAYS_DATE, LOGGER


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
        if (start_date and not end_date) or (not start_date and end_date):
            raise exceptions.InvalidDateException(
                "end_date must be specified if start_date is provided"
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

    except exceptions.InvalidDateException as exception:
        LOGGER.error("Error in __init__: %s", exception, exc_info=True)
        raise exceptions.InvalidDateException(f"Error in __init__: {exception}")


def date_range(start_date, end_date):
    """
    return range of all date between given date
    if not end_date then take start_date as end date
    """
    try:
        total_days = int((end_date - start_date).days)
        if total_days > 30:
            raise exceptions.InvalidDateException("Date must be in range of 30 days")
        else:
            for date in range(total_days + 1):
                yield start_date + timedelta(date)
    except exceptions.InvalidDateException as exception:
        raise exceptions.InvalidDateException(f"Error in __init__: {exception}")


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param d: Input dictionary.
    :type d: dict
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


def get_raw_response(response):
    """
    extracts raw data from web page and returns a dictionary
    Parameters:
        response(object): web page
    Returns
        raw_resopnse(dictionary): available raw data
    """
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
        image_objects = []
        video_objects = []
        other_data = []
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
        for ld_json in ld_json_data:
            data = json.loads(ld_json)
            if data.get("@type") == "NewsArticle" or "BlogPosting":
                parsed_json["main"] = data
            elif "ImageObject" in data.get("@type"):
                image_objects.append(data)
            elif "VideoObject" in data.get("@type"):
                video_objects.append(data)
            else:
                other_data.append(data)

        parsed_json["imageObjects"] = image_objects
        parsed_json["videoObjects"] = video_objects
        parsed_json["other"] = other_data
        return remove_empty_elements(parsed_json)

    except BaseException as exception:
        LOGGER.info("Error occured while getting parsed json %s", exception)
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
        pattern = r"[\r\n\t]+"
        main_dict = {}
        main_data = get_main(response)
        main_dict["description"] = [response.css("meta[property=\"og:description\"]::attr(content)").get()]

        title = main_data.get("headline")
        if title:
            title = re.sub(pattern, "", title).strip()
            main_dict["title"] = [title]

        main_dict["published_at"] = [main_data.get("datePublished")]

        main_dict["modified_at"] = [main_data.get("dateModified")]

        main_dict["author"] = [main_data.get("author")]

        main_dict["section"] = [main_data.get("articleSection")]

        main_dict["publisher"] = [main_data.get("publisher")]

        main_dict["text"] = get_content(response)

        main_dict["tags"] = get_tags(response)

        main_dict["thumbnail_image"] = [main_data.get("image")]

        main_dict["images"] = get_images(response)

        mapper = {"it-IT": "Italian"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        main_dict["video"] = get_video(response)

        return remove_empty_elements(main_dict)
    except BaseException as exception:
        LOGGER.error("while scrapping parsed data %s", exception)
        raise exceptions.ArticleScrappingException(
            f"while scrapping parsed data :{exception}"
        )


def get_main(response):
    """
    get the main data for the article
    Args:
        response: provided response
    Returns:
        dict: main data related details
    """
    ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
    for ld_json in ld_json_data:
        if "NewsArticle" or "BlogPosting" in ld_json:
            return json.loads(ld_json)

def get_tags(response):
    """
    get the tags for the article
    Args:
        response: provided response
    Returns:
        dict: tags related details
    """
    tags = response.css("meta[property=\"article:tag\"]::attr(content)").getall()
    if tags:
        return tags


def get_video(response):
    """
    get the video for the article
    Args:
        response: provided response
    Returns:
        dict: video related details
    """
    ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
    data={}
    for ld_json in ld_json_data:
        if "VideoObject" in ld_json:
            data =  json.loads(ld_json)
    if data:
        video_url = data.get("contentUrl")
        return [video_url]


def get_content(response):
    """
    function to get the text content for the given article
    Args:
        response: provided response
    Returns:
        dict: text related details
    """
    article_content = response.css("section.article-content p").getall()
    content = [remove_tags(i) for i in article_content]
    text = " ".join(content)
    if text:
        return [re.sub(r"[\n\t\r\"]", "", text).strip()]

def get_images(response):
    data = []
    images = response.css("div.swiper-slide.swiper-change-height a::attr(href)").getall()
    multi_images = response.css("img.alignnone.size-full::attr(src)").getall()
    article_img = response.css("picture.main-image-article img::attr(src)").get()
    if article_img:
        data.append({"link":article_img})
    if images:
        for img in range(len(images)):
            temp_dict = {}
            temp_dict["link"] = images[img]
            data.append(temp_dict)
    if multi_images:
        for img in range(len(multi_images)):
            temp_dict = {}
            temp_dict["link"] = multi_images[img]
            data.append(temp_dict)
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
    except BaseException as exception:
        LOGGER.error("error while creating json file: %s", exception)
        raise exceptions.ExportOutputFileException(
            f"error while creating json file: {exception}"
        )