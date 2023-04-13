"""Utility/helper functions"""
# utils.py

import os
import re
import json
import logging
from datetime import datetime, timedelta
from crwndtv import exceptions
from crwndtv.constant import TODAYS_DATE, LOGGER


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
        pattern = r"[\r\n\t\</h2>\<h2>]+"
        main_dict = {}
        main_data = get_main(response)

        main_dict["description"] = [
            response.css('meta[property="og:description"]::attr(content)').get()
        ]

        title = response.css('meta[property="og:title"]::attr(content)').get()
        if title:
            title = re.sub(pattern, "", title).strip()
            main_dict["title"] = [title]

        main_dict["published_at"] = [
            response.css("meta[name='publish-date']::attr(content)").get()
        ]

        main_dict["modified_at"] = get_modified_date(response)

        author = get_author(response)
        if author:
            main_dict["author"] = author

        main_dict["section"] = get_section(response)

        if main_data:
            if main_data.get("publisher"):
                main_dict["publisher"] = [main_data["publisher"]]
            else:
                main_dict["publisher"] = []

        main_dict["text"] = get_content(response)
        main_dict["tags"] = (
            response.css('meta[name="keywords"]::attr(content)').get().split(",")
        )

        thumbnail_image = response.css('meta[property="og:image"]::attr(content)').get()
        if thumbnail_image:
            main_dict["thumbnail_image"] = [thumbnail_image]
        main_dict["images"] = get_images(response)
        source_language = "English"
        main_dict["source_language"] = [source_language]

        video = get_video(response)
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
    ld_json = response.css(
        'script[type="application/ld+json"]:contains("description")::text'
    ).get()
    if ld_json:
        return json.loads(ld_json)


def get_author(response):
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: author related details
    """
    author = {}
    author_name = response.css("span[itemprop='author'] span::text").getall()
    author_second_name = response.css("span[itemprop='author'] span a::text").get()
    author_url = response.css("span[itemprop='author'] meta[itemprop='url']\
                              ::attr(content)").getall()
    author_second_url = response.css("a.pst-by_lnk::attr(href)").get()
    if len(author_name) == 2:
        tmp_list = []
        for i in range(0, len(author_name)):
            tmp_dict = {}
            tmp_dict["name"] = author_name[i]
            tmp_dict["url"] = author_url[i]
            tmp_list.append(tmp_dict)
        return tmp_list
    if len(response.css("span[itemprop='author'] span").getall()) == 1:
        if author_name and author_url:
            author["name"] = author_name[0]
            author["url"] = author_url[0]
        elif author_name and author_second_url:
            author["name"] = author_name[0]
            author["url"] = author_second_url
        elif author_second_name and author_url:
            author["name"] = author_second_name
            author["url"] = author_url[0]
        elif author_second_name and author_second_url:
            author["name"] = author_second_name
            author["url"] = author_second_url
        return [author]
    if len(response.css("span[itemprop='author'] span").getall()) == 2:
        author["name"] = author_second_name
        author["url"] = author_second_url
        return [author]


def get_images(response):
    """
    get the images for the article
    Args:
        response: provided response
    Returns:
        dict: images related details
    """
    images = []
    image = response.css("div.ntv_vidgall_img img::attr(src)").getall()
    image_caption = response.css("div.ntv_description::text").getall()
    for i in range(len(image)):
        temp_dict = {}
        temp_dict["link"] = image[i]
        temp_dict["caption"] = image_caption[i]
        images.append(temp_dict)
    return images


def get_modified_date(response):
    """
    get the modified date for the article
    Args:
        response: provided response
    Returns:
        dict: modified date related details
    """
    modified_date_vid = response.css(
        ".pst-by_ul span.pst-by_lnk span[itemprop]::attr(content)"
    ).get()
    if modified_date_vid:
        return [modified_date_vid]
    modified_date_img = response.css("span.time_stamp::text").get()
    if modified_date_img:
        return [modified_date_img[9:]]
    modified_date = response.css('meta[name="modified-date"]::attr(content)').get()
    if modified_date:
        return [modified_date]


def get_section(response):
    """
    function to get section for the given article
    Args:
        response: provided response
    Returns:
        dict: section related details
    """
    section = response.css("span.brd-nv_li.current span::text").get()
    if section:
        return [section]
    section_vid = response.css('a[title="Video"]::attr(title)').get()
    if section_vid:
        return [section_vid]
    section_img = response.css('a[title="Photos"]::attr(title)').get()
    if section_img:
        return [section_img]


def get_content(response):
    """
    function to get the text content for the given article
    Args:
        response: provided response
    Returns:
        dict: text related details
    """
    ld_json = get_parsed_json(response)
    pattern = r"[\n\t\r\"]"
    article_content = response.css(
        "div.sp-cn.ins_storybody p[class!='ins_instory_dv_caption sp_b']::text"
    ).getall()
    text = " ".join(article_content)
    if text:
        return [re.sub(pattern, "", text).strip()]

    elif ld_json.get("main", None):
        return ld_json.get("main")['articleBody']


def get_video(response):
    """
    function to get video content for the article
    Args:
        response: provided response
    Returns:
        dict: video related details
    """
    video = {}
    article_video = response.css('meta[itemprop="embedUrl"]::attr(content)').get()
    if article_video:
        video["link"] = article_video
    article_video_2 = response.css('meta[itemprop="contentUrl"]::attr(content)').get()
    if article_video_2:
        video["link"] = article_video_2
    video_link = response.xpath('//meta[@name="contentUrl"]/@content').get()
    if video_link:
        video["link"] = video_link
    return video


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
