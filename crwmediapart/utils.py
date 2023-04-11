# Utility/helper functions
# utils.py

import re
import json
import logging
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from crwmediapart import exceptions
from crwmediapart.constant import TODAYS_DATE, LOGGER


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
        exceptions.InvalidDateException: _description_
        exceptions.InvalidDateException: _description_
        exceptions.InvalidDateException: _description_
        exceptions.InvalidDateException: _description_
        exceptions.InvalidDateException: _description_
        exceptions.InvalidDateException: _description_
    """
    start_date = (datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None)
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    try:
        if start_date and not end_date:
            raise exceptions.InvalidDateException("end_date must be specified if start_date is provided")
        if not start_date and end_date:
            raise exceptions.InvalidDateException("start_date must be specified if end_date is provided")

        if start_date and end_date and start_date > end_date:
            raise exceptions.InvalidDateException("start_date should not be later than end_date")

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException("start_date should not be greater than today_date")

        if start_date and end_date and end_date > TODAYS_DATE:
            raise exceptions.InvalidDateException("end_date should not be greater than today_date")

    except exceptions.InvalidDateException as expception:
        LOGGER.info(
            f"Error occured while checking date range: {expception}"
        )
        raise exceptions.InvalidDateException(
            f"Error occured while checking date range: {expception}"
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
        return value is None or value == {} or value == []

    if not isinstance(parsed_data_dict, (dict, list)):
        data_dict = parsed_data_dict
    elif isinstance(parsed_data_dict, list):
        data_dict = [value for value in (remove_empty_elements(value) for value in parsed_data_dict)
                     if not empty(value)]
    else:
        data_dict = {
            key: value
            for key, value in (
                (key, remove_empty_elements(value)) for key, value in parsed_data_dict.items()
            )
            if not empty(value)
        }

    return data_dict


def get_raw_response(response):
    """generate dictrionary of raw html data

    Args:
        response (object): page_data

    Returns:
        raw_response (dict): targeted data
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
        imageObjects = []
        videoObjects = []
        other_data = []
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
        for a_block in ld_json_data:
            data = json.loads(a_block)
            if data.get("@type") == "NewsArticle":
                parsed_json["main"] = data
            elif data.get("@type") in {"ImageGallery", "ImageObject"}:
                imageObjects.append(data)
            elif data.get("@type") == "VideoObject":
                videoObjects.append(data)
            else:
                other_data.append(data)

        parsed_json["imageObjects"] = imageObjects
        parsed_json["videoObjects"] = videoObjects
        parsed_json["other"] = other_data
        misc = get_misc(response)
        if misc:
            parsed_json["misc"] = misc
        return remove_empty_elements(parsed_json)

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed json {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occurred while getting parsed json {exception}"
        )


def get_parsed_data(response):
    """
    Extracts data from a news article webpage and returns it in a dictionary format.

    Parameters:
    response (scrapy.http.Response): A scrapy response object of the news article webpage.

    Returns:
    dict: A dictionary containing the extracted data from the webpage, including:
         - 'publisher': (str) The name of the publisher of the article.
         - 'article_catagory': The region of the news that the article refers to
         - 'headline': (str) The headline of the article.
         - 'authors': (list) The list of authors of the article, if available.
         - 'published_on': (str) The date and time the article was published.
         - 'updated_on': (str) The date and time the article was last updated, if available.
         - 'text': (list) The list of text paragraphs in the article.
         - 'images': (list) The list of image URLs in the article, if available. (using bs4)

    """
    try:
        main_dict = {}
        publisher = get_publisher(response)
        main_dict["publisher"] = publisher

        main_data = get_main(response)
        headline = main_data[0].get("headline")
        main_dict["title"] = [headline]

        author = main_data[0].get("author")
        main_dict["author"] = author

        thumbnail_image = main_data[0].get("image")
        main_dict["thumbnail_image"] = thumbnail_image

        main_dict["published_at"] = [main_data[0].get("datePublished")]
        main_dict["modified_at"] = [main_data[0].get("dateModified")]

        description = main_data[0].get("description")
        main_dict["description"] = [description]

        article_text = response.css("div.news__body__center__article p::text").getall()
        if article_text:
            main_dict["text"] = [(" ".join(article_text).replace("\n", "")).strip()]

        mapper = {"FRA": "France", "fr-FR": "French", "fr": "French"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_main(response) -> list:
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

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting main: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting main: {exception}"
        )


def get_misc(response) -> list:
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
        LOGGER.info(f"Error occured while extracting misc: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting misc: {exception}"
        )


def get_publisher(response) -> list:
    """
    Extracts publisher information from the given response object and returns it as a dictionary.

    Returns:
    - A dictionary containing information about the publisher.The dictionary has the following keys:
    ---
    @id: The unique identifier for the publisher.
    @type: The type of publisher (in this case, always "NewsMediaOrganization").
    name: The name of the publisher.
    logo: Logo of the publisher as an image object
    """
    try:
        logo = response.css('head link[rel="icon"]::attr(href)').get()
        img_response = requests.get(logo)
        width, height = Image.open(BytesIO(img_response.content)).size
        a_dict = {
            "@id": "mediapart.fr",
            "@type": "NewsMediaOrganization",
            "name": "Global NEWS",
            "logo": {
                "@type": "ImageObject",
                "url": logo,
                "width": {"@type": "Distance", "name": str(width) + " px"},
                "height": {"@type": "Distance", "name": str(height) + " px"},
            },
        }
        return [a_dict]

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting publisher: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting publisher: {exception}"
        )


def get_author(response) -> list:
    """
            The extract_author function extracts information about the author(s)
            of an article from the given response object and returns it in the form of a list of dictionaries.

            Parameters:
                response (scrapy.http.Response): The response object containing the HTML of the article page.

            Returns:
                A list of dictionaries, where each dictionary contains information about one author.

            """
    try:
        info = response.css("div.splitter__first p a")
        pattern = r"[\r\n\t\"]+"
        data = []
        if info:
            for i in info:
                temp_dict = {}
                temp_dict["@type"] = "Person"
                name = i.css("a::text").get()
                if name:
                    name = re.sub(pattern, "", name).strip()
                    temp_dict["name"] = "".join((name.split("("))[0::-2])
                    url = i.css("a::attr(href)").get()
                    if url:
                        temp_dict["url"] = "https://www.mediapart.fr" + url
                    data.append(temp_dict)
            return data

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting author: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting author: {exception}"
        )
