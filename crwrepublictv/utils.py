# Utility/helper functions
# utils.py

import re
import json
import requests
import logging
from datetime import datetime
from crwrepublictv import exceptions
from crwrepublictv.constant import TODAYS_DATE, LOGGER


pattern = r"[\r\n\t\"]+"


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    """validate date range given by user
    Args:
        start_date (datetime): start_date
        end_date (datetime): end date
    Raises:
        exceptions.InvalidDateException: end_date must be specified if start_date is provided
        exceptions.InvalidDateException: start_date must be specified if end_date is provided
        exceptions.InvalidDateException: start_date should not be later than end_date
        exceptions.InvalidDateException: start_date should not be greater than today_date
        exceptions.InvalidDateException: end_date should not be greater than today_date
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
                "end_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as expception:
        LOGGER.info(f"Error occured while checking date range: {expception}")
        raise exceptions.InvalidDateException(
            f"Error occured while checking date range: {expception}"
        )


def get_raw_response(response):
    """generate dictrionary of raw html data
    Args:
        response (object): page_data
    Returns:
        raw_response (dict): targeted data
    """
    try:
        raw_resopnse = {
            "content_type": "text/html; charset=utf-8",
            "content": response.css("html").get(),
        }
        return raw_resopnse
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting raw response: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting raw response: {exception}"
        )


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

    except Exception as exception:
        LOGGER.info(f"Error while parsing json from application/ld+json: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsing json from application/ld+json: {exception}"
        )


def get_main(response):
    """
    returns a list of main data available in the article from application/ld+json
    Parameters:
        response:
    Returns:
        main data
    """
    try:

        information = {}
        main = response.css('script[type="application/ld+json"]::text').getall()
        for block in main:
            data = json.loads(block)
            if data.get("@type") == "NewsArticle":
                information["article"] = data
            elif data.get("@type") == "WebPage":
                information["WebPage"] = data
            elif data.get("@type") == "VideoObject":
                information["VideoObject"] = data
            elif data.get("@type") == "BreadcrumbList":
                information["BreadcrumbList"] = data
            else:
                pass
        return information
    except BaseException as exception:
        LOGGER.info("Error while getting main %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error while getting main: {exception}"
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
        LOGGER.info(f"Error occured while getting misc: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting misc: {exception}"
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


def get_parsed_data(response):
    """
    Extracts data from a news article webpage and returns it in a dictionary format.

    Parameters:
    response (scrapy.http.Response): A scrapy response object of the news article webpage.

    Returns:
    dict: A dictionary containing the extracted data from the webpage, including:
        - 'breadcrumbs': (list) The list of breadcrumb links to the article, if available.
        - 'published_on': (str) The date and time the article was published.
        - 'last_updated': (str) The date and time the article was last updated, if available.
        - 'headline': (str) The headline of the article.
        - 'description': (str) The description of the article, if available.
        - 'publisher': (str) The name of the publisher of the article.
        - 'authors': (list) The list of authors of the article, if available.
        - 'video': (str) The video URL of the article, if available.
        - 'thumbnail_image': (str) The URL of the thumbnail image of the article, if available.
        - 'subheadings': (list) The list of subheadings in the article, if available.
        - 'text': (list) The list of text paragraphs in the article.
        - 'images': (list) The list of image URLs in the article, if available.
    """
    try:
        parsed_data = {}
        main_data = get_main(response)
        article_json = main_data.get("article")
        videoobject_json = main_data.get("VideoObject")
        web_page_json = main_data.get("WebPage")
        breadcrumbs = main_data.get("BreadcrumbList")
        if article_json:
            main_data = article_json
        else:
            main_data = videoobject_json

        parsed_data = get_parsed_data_dict()
        # get author and published,modified date
        parsed_data |= get_author_dates(main_data, response)
        # get description and publisher info and title
        parsed_data |= get_description_publisher_title(
            web_page_json, main_data, response
        )
        # get section information
        parsed_data |= get_section(breadcrumbs)
        article_text = response.css("section p::text").getall()
        parsed_data["text"] = [" ".join(article_text)]
        # get thumbnail url
        thumbnail = get_thumbnail_image(response)
        parsed_data["thumbnail_image"] = thumbnail
        # get images from article
        article_images = get_images(response)
        parsed_data["images"] = article_images
        # get embedded video links
        video = get_embed_video_link(response)
        parsed_data["embed_video_link"] = video
        # get source language details
        mapper = {"en": "English", "hi_IN": "Hindi"}
        article_lang = response.css("html::attr(lang)").get()
        parsed_data["source_language"] = [mapper.get(article_lang)]
        parsed_data["tags"] = get_tags(response)

        final_dict = remove_empty_elements(parsed_data)
        return format_dictionary(final_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_section(breadcrumbs_dict):

    section = ""
    if breadcrumbs_dict:
        for item in breadcrumbs_dict.get("itemListElement"):
            if item.get("position") == 2:
                section = (item.get("item")).get("name")
        return {"section": section}
    else:
        return {"section": None}


def get_author_dates(parsed_json_dict, response):
    """extracts author and published data,modified data inforomation

    Args:
        parsed_json_dict (dict): parsed_main data ld+json
        response (str): page response

    Returns:
        dict: values with published_at modified_at and author
    """
    try:
        if parsed_json_dict:
            return {
                "author": parsed_json_dict.get("author", None),
                "modified_at": parsed_json_dict.get("dateModified", None),
                "published_at": parsed_json_dict.get("datePublished", None)
                or parsed_json_dict.get("uploadDate", None),
            }
        elif response.css("div.padtop20") or response.css("div.author"):
            authors = response.css("div.author")
            author_data = []
            if authors:
                for author in authors:
                    temp_dict = {}
                    temp_dict["@type"] = "Person"
                    temp_dict["name"] = re.sub(
                        pattern, "", author.css("div a span::text").get()
                    ).strip()
                    temp_dict["url"] = author.css("div a::attr(href)").get()
                    author_data.append(temp_dict)
            return {
                "published_at": response.css("time::attr(datetime)").get(),
                "modified_at": response.css(
                    "span.time-elapsed time::attr(datetime)"
                ).get(),
                "author": author_data,
            }
        else:
            return {
                "published_at": None,
                "modified_at": None,
                "author": None,
            }
    except Exception as exception:
        LOGGER.info(f"error while getting last updated: {exception}")
        raise exceptions.ArticleScrappingException(
            f"error while getting last updated: {exception}"
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


def get_tags(response):
    try:
        tags = []
        raw_tags = response.css('meta[name="keywords"]::attr(content)').get()
        if raw_tags:
            return raw_tags.split(",")
        return tags
    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting tags: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting tags: {exception}"
        )


def get_thumbnail_image(response) -> list:
    """
    The function extract_thumbnail extracts information about the thumbnail image(s) associated with a webpage,
    including its link, width, and height, and returns the information as a list of dictionaries.

    Returns:
        A list of dictionaries, with each dictionary containing information about an image.
            If no images are found, an empty list is returned.
    """
    try:
        info = response.css("div.gallery-item")
        mod_info = response.css(".storypicture img.width100")
        data = []
        if info:
            for block in info:
                image = block.css("div.gallery-item-img-wrapper img::attr(src)").get()
                if image:
                    data.append(image)
        elif mod_info:
            for block in mod_info:
                image = block.css("img::attr(src)").get()
                if image:
                    data.append(image)
        return data
    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting thumbnail image: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting thumbnail image: {exception}"
        )


def get_embed_video_link(response) -> list:
    """
    A list of video objects containing information about the videos on the webpage.
    """
    try:
        info = response.css("div.videoWrapper")
        data = []
        if info:
            for block in info:
                js = block.css("script").getall()
                for block in js:
                    request_link = re.findall(r"playlist\s*:\s*'(\S+)'", block)
                    if request_link:
                        response = requests.get(request_link[0])
                        link = (
                            response.json()
                            .get("playlist")[0]
                            .get("sources")[1]
                            .get("file")
                        )
                        data.append(link)
        return data
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting video links: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting video links: {exception}"
        )


def get_description_publisher_title(web_page_dict, parsed_json_dict, response):
    """get description and publisher if available

    Args:
        web_page_dict (dict): webpage data from ld+json
        response (str): response string of page
    """
    if web_page_dict:
        return {
            "description": web_page_dict.get("description", None),
            "publisher": web_page_dict.get("publisher", None)
            or parsed_json_dict.get("publisher", None),
            "title": web_page_dict.get("name", None)
            or parsed_json_dict.get("headline", None),
        }
    elif response.css("h1.story-title::text"):
        headline = response.css("h1.story-title::text").get().strip()
        return {"description": None, "publisher": None, "title": headline}
    else:
        return {"description": None, "publisher": None, "title": None}


def get_images(response) -> list:
    """
    Extracts all the images present in the web page.

    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    try:
        info = response.css("div.embedpicture")
        data = []
        if info:
            for block in info:
                temp_dict = {}
                image = block.css("div.embedimgblock img::attr(src)").get()
                if image:
                    temp_dict["link"] = image
                data.append(temp_dict)
        return data
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article images: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting article images: {exception}"
        )


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
