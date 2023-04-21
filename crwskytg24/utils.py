"""Utility/helper functions"""
# utils.py

import os
import re
import json
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
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
        ld_json_data = [
            json.loads(ld_json)
            for ld_json in response.css(
                'script[type="application/ld+json"]::text'
            ).getall()
        ]

        for ld_json in ld_json_data[0]:
            if ld_json.get("@type") == "NewsArticle":
                parsed_json["main"] = ld_json
            elif "ImageObject" in ld_json.get("@type"):
                image_objects.append(ld_json)
            elif "VideoObject" in ld_json.get("@type"):
                video_objects.append(ld_json)
            else:
                other_data.append(ld_json)

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
        main_dict = {}
        main_data = get_main(response)
        main_dict["description"] = [
            response.css('meta[property="og:description"]::attr(content)').get()
        ]

        main_dict["title"] = [
            response.css('meta[property="og:title"]::attr(content)').get()
        ]

        main_dict["published_at"] = [main_data.get("datePublished")]

        main_dict["modified_at"] = [main_data.get("dateModified")]

        main_dict["author"] = [main_data.get("author")]

        main_dict["section"] = [main_data.get("articleSection")]

        main_dict["publisher"] = [main_data.get("publisher")]

        main_dict["text"] = get_content(response)

        main_dict["tags"] = main_data.get("keywords")

        main_dict["thumbnail_image"] = [main_data.get("thumbnailurl")]

        main_dict["images"] = get_images(response)

        mapper = {"it": "Italian"}
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
    ld_json_data = json.loads(
        response.css('script[type="application/ld+json"]::text').get()
    )
    for ld_json in ld_json_data:
        if "NewsArticle" in ld_json.get("@type"):
            return ld_json


def get_images(response):
    """
    function to get the images from the response
    Args: response object
    returns: list of images and caption
    """
    images_block = response.css("div.c-gallery-item__content-wrapper")
    intro_image = response.css("img.c-intro__img::attr(src)").get()
    image_gallery = response.css(
        "div.s-gallery-inline div.c-inline-gallery__carousel-wrapper img"
    )
    image_gallery_caption = response.css(
        "div.s-gallery-inline div.c-inline-gallery__text p"
    )
    hero_image = response.css(
        "div.c-hero.c-hero--reverse-m.c-hero--reverse-t.c-hero--bg-colored-m img[class='c-hero__img']::attr(src)"
    ).get()
    image_between_block = response.css("div[class='c-inline-image l-spacing-m'] figure")
    data = []
    if hero_image:
        dict = {}
        dict["link"] = hero_image
        data.append(dict)
    if intro_image:
        dict = {}
        dict["link"] = intro_image
        data.append(dict)
    if images_block:
        for image in images_block:
            temp_dict = {}
            temp_dict["link"] = image.css(
                "noscript img.c-gallery-item__img::attr(src)"
            ).get()
            caption = image.css("p.c-gallery-item__caption::text").getall()

            temp_dict["caption"] = "".join(
                [re.sub(r"[\r\n\t]+", "", cap).strip() for cap in caption]
            )
            data.append(temp_dict)
    if image_gallery:
        for image, caption in zip(image_gallery, image_gallery_caption):
            temp_dict = {}
            temp_dict["link"] = image.css("img::attr(src)").get()
            temp_dict["caption"] = caption.css("p::text").get()
            data.append(temp_dict)
    if image_between_block:
        for article in image_between_block:
            temp_dict = {}
            temp_dict["link"] = article.css("noscript img::attr(src)").get()
            temp_dict["caption"] = article.css("figcaption::text").get()
            data.append(temp_dict)
    return data


def get_content(response):
    """
    function to get content from the response object
    Args: response object 
    Returns: content list
    """
    article_first = response.css("div.c-article-abstract p::text").get()
    article_content = response.css(
        "div.c-article-section.j-article-section.l-spacing-m"
    ).getall()
    article_content_list = []
    for article in article_content:
        if article:
            soup = BeautifulSoup(article, "html.parser")
            for div in soup.find_all("a", {"class": "c-inline-card"}):
                div.decompose()
            article_content_list.append(str(soup))
    content = [
        re.sub(r"[\r\n\t]+", "", remove_tags(article)).strip() for article in article_content_list
    ]
    article = "".join(content)
    if article_first and article:
        return [article_first + article]
    return [article_first]


def get_video(response):
    """
    function to get video information

    Arguments: response object 
    return: list of video links
    """
    ld_json_data = json.loads(
        response.css('script[type="application/ld+json"]::text').get()
    )
    data = {}
    for ld_json in ld_json_data:
        if ld_json.get("@type") == "VideoObject":
            data = ld_json
    if data:
        return [data.get("embedUrl")]


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
