""" General functions """
import json
import logging
from datetime import datetime
from crwbastillepost import exceptions
from crwbastillepost.constant import TODAYS_DATE, LOGGER
import itertools
import re


def create_log_file():
    """creates log file"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    """validate the sitemap arguments"""
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

    except exceptions.InvalidDateException as expception:
        LOGGER.info(f"Error occured while checking date range: {expception}")
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


def get_main(response):
    """
    returns a list of main data available in the article from application/ld+json
    Parameters:
        response:
    Returns:
        main data
    """
    try:
        SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"
        main = response.css('script[type="application/ld+json"]::text').getall()
        json_format = re.sub(SPACE_REMOVER_PATTERN, "", main[0]).strip()
        data = json.loads(json_format)
        return data

    except BaseException as exception:
        LOGGER.error("Error while getting main %s ", exception)
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


def get_raw_response(response):
    """
    Raw response data generated from given response and selector

    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector

    Returns:
        Dictionary with generated raw response
    """

    raw_resopnse = {
        "content_type": response.headers.get("Content-Type").decode("utf-8"),
        "content": response.text,
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
    SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"
    parsed_json = {}
    other_data = []
    ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
    for a_block in ld_json_data:
        json_format = re.sub(SPACE_REMOVER_PATTERN, "", a_block).strip()
        data = json.loads(json_format)
        if data.get("@type") == "NewsArticle":
            parsed_json["main"] = data
        elif data.get("@type") in ["ImageGallery", "ImageObject"]:
            parsed_json["imageObjects"] = data
        elif data.get("@type") == "VideoObject":
            parsed_json["videoObjects"] = data
        else:
            other_data.append(data)

    parsed_json["Other"] = other_data
    misc = get_misc(response)
    if misc:
        parsed_json["misc"] = misc

    return remove_empty_elements(parsed_json)


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

        headline = response.css("h1.cat-theme-color::text").getall()
        main_dict["title"] = headline

        authors = get_author(response)
        main_dict["author"] = authors

        main_data = get_main(response)
        main_dict["description"] = [main_data.get("description")]

        main_dict["published_at"] = [main_data.get("datePublished")]

        main_dict["modified_at"] = [main_data.get("dateModified")]

        main_dict["section"] = [main_data.get("articleSection")]
        main_dict["tags"] = main_data.get("keywords")

        thumbnail_image = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail_image

        article_text = response.css("p::text").getall()
        main_dict["text"] = [" ".join(article_text)]

        images = get_images(response)
        if images:
            main_dict["images"] = images

        videos = response.css("video source::attr(src)").getall()
        main_dict["embed_video_link"] = videos

        main_dict["source_language"] = ["Chinese"]
        main_dict["source_country"] = ["China"]
        main_dict["time_scraped"] = [str(datetime.now())]

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_publisher(response):
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
        SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"
        response = response.css('script[type="application/ld+json"]::text').getall()
        json_format = re.sub(SPACE_REMOVER_PATTERN, "", response[0]).strip()
        json_loads = json.loads(json_format)
        data = []
        publisher = json_loads.get("publisher")
        data.append(publisher)
        return data

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting publisher: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting publisher: {exception}"
        )


def get_author(response) -> list:
    """
    The get_author function extracts information about the author(s)
    of an article from the given response object and returns it in the form of a list of dictionaries.
    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        A list of dictionaries, where each dictionary contains information about one author.
    """
    try:
        SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"
        parsed_data = response.css('script[type="application/ld+json"]::text').getall()
        if parsed_data:
            for block in parsed_data:
                json_format = re.sub(SPACE_REMOVER_PATTERN, "", block).strip()
                if "NewsArticle" in json.loads(json_format).get("@type", [{}]):
                    data = []
                    var = {
                        "@type": json.loads(json_format)
                        .get("author", [{}])
                        .get("@type"),
                        "name": json.loads(json_format).get("author", [{}]).get("name"),
                        "url": json.loads(json_format)
                        .get("author", [{}])
                        .get("url", None),
                    }
                    data.append(var)
            return data

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting author: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting author: {exception}"
        )


def get_thumbnail_image(response) -> list:
    """extracting thumbnail image from application+ld/json data in main function
    Args:
        response (obj): page_object
    Returns:
        list: list of thumbnail images
    """
    try:
        image = get_main(response)
        thumbnail_image = []
        thumbnail_image.append(image.get("image").get("url"))
        return thumbnail_image

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting thumbnail image: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting thumbnail image: {exception}"
        )


def get_images(response) -> list:
    """extracting image links from provided response
    Args:
        response (_type_): html page object
    Returns:
        list: list of images inside the article
    """
    try:
        temp_dict = {
            "images": [
                {"link": img, "caption": cap}
                for img, cap in itertools.zip_longest(
                    response.css(".wp-caption a::attr(href)").getall(),
                    response.css(".wp-caption-text::text").getall()
                    + response.css("span.custom-caption::text").getall(),
                    fillvalue=None,
                )
            ]
        }
        return temp_dict.get("images")

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article images: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting article images: {exception}"
        )
