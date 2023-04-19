"""Utility/helper functions"""
# utils.py

import os
import re
import json
import logging
from datetime import datetime, timedelta
from crwilfattoquotidiano import exceptions
from crwilfattoquotidiano.constant import TODAYS_DATE, LOGGER


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
            data = json.loads(ld_json)[0]
            if data.get("@type") == "NewsArticle":
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
        main_dict["description"] = [main_data[0].get("description")]

        title = response.css('meta[property="og:title"]::attr(content)').get()
        if title:
            title = re.sub(pattern, "", title).strip()
            main_dict["title"] = [title]

        main_dict["published_at"] = [main_data[0].get("datePublished")]

        main_dict["modified_at"] = [main_data[0].get("dateModified")]

        main_dict["author"] = [main_data[0].get("author")]

        main_dict["section"] = [
            response.css(
                "a.breadcrumb__link.u-typo.u-typo--breadcrumb-link::text"
            ).getall()[0]
        ]

        main_dict["publisher"] = [main_data[0].get("publisher")]

        main_dict["text"] = get_content(response)

        main_dict["tags"] = get_tags(response)

        main_dict["thumbnail_image"] = [
            response.css('meta[property="og:image"]::attr(content)').get()
        ]

        main_dict["images"] = get_images(response)
        source_language = "English"
        main_dict["source_language"] = [source_language]

        video = main_data[0].get("embedUrl")
        if video:
            main_dict["video"] = [video]

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
    ld_json = response.css('script[type="application/ld+json"]::text').get()
    if ld_json:
        return json.loads(ld_json)


def get_content(response):
    """
    get the content for the article
    Args:
        response: provided response
    Returns:
        list: content related details
    """
    pattern = r"[\n\t\r\"]"
    content = response.css("p.text-element.u-richtext.u-typo.u-typo--article-text.article__text-element.text-element--context-article::text").getall()
    text = " ".join(content)
    if text:
        return [re.sub(pattern, "", text).strip()]


def get_images(response):
    """
    get images for the article
    Args:
        response: provided response
    Returns:
    """
    images = []
    image = response.css("img.image.image-element__image::attr(src)").getall()
    image_caption = response.css(
        "figcaption.image-element__caption div.image\
                                 -element__description.u-richtext.u-typo.u-typo--caption::text"
    ).getall()

    image_second = response.css("img.image.group-gallery__img::attr(src)").getall()
    image_caption_second = response.css(
        "img.image.group-gallery__img::attr(alt)"
    ).getall()

    if image:
        new_caption = [re.sub('[\n\t\r"]', "", s).strip() for s in image_caption]
        caption = [x for x in new_caption if x != ""]

        for i in range(len(image)):
            temp_dict = {}
            temp_dict["link"] = image[i]
            if caption:
                temp_dict["caption"] = caption[i]
            images.append(temp_dict)
        return images

    if image_second:
        for i in range(len(image_second)):
            temp_dict = {}
            temp_dict["link"] = image_second[i]
            if image_caption_second:
                temp_dict["caption"] = image_caption_second[i]
            temp_dict["caption"] = image_caption_second[i]
            images.append(temp_dict)
        return images


def get_tags(response):
    """
    get the tags for the article
    Args:
        response: provided response
    Returns:
        list: tags related details
    """
    img_tags = response.css('meta[property="article:tag"]::attr(content)').getall()
    vid_tags = response.css('meta[property="video:tag"]::attr(content)').getall()
    if img_tags:
        return img_tags
    if vid_tags:
        return vid_tags


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