"""General functions"""
import os
import json
import logging
from datetime import datetime
import re
from crwlarepublica import exceptions
from crwlarepublica.constant import TODAYS_DATE, LOGGER


def create_log_file():
    """creates log file"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    """validate the sitemap arguments """

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

    except exceptions.InvalidDateException as exception:
        LOGGER.info(f"Error occured while checking date range: {exception}")
        raise exceptions.InvalidDateException(
            f"Error occured while checking date range: {exception}"
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
        data = []
        response = response.css('script[type="application/ld+json"]::text').getall()
        data.append(json.loads(response[0]))
        return data

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting main: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting main: {exception}"
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
    try:
        # breakpoint()
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
            f"Error occured while getting parsed json {exception}"
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
        pattern = r"[\r\n\t\"]+"
        main_dict = {}
        publisher = get_publisher(response)
        main_dict["publisher"] = publisher

        headline = response.css(".story__header__content h1::text").getall()
        main_dict["title"] = headline

        authors = get_author(response)
        main_dict["author"] = authors

        main_dict["description"] = response.css(
            "meta[name='description']::attr(content)"
        ).getall()

        main_data = get_main(response)
        main_dict["published_at"] = [main_data[0].get("datePublished")]
        main_dict["modified_at"] = [main_data[0].get("dateModified")]

        thumbnail_image = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail_image

        article_text = response.css(
            "div.story__summary::text, div.story__content p::text"
        ).getall()
        text = [re.sub(pattern, "", i) for i in article_text]

        main_dict["text"] = [" ".join(text)]

        videos = get_embed_video_link(response)
        main_dict["embed_video_link"] = videos
        main_dict["source_language"] = ["Italian"]

        main_dict["source_country"] = ["Italy"]
        main_dict["time_scraped"] = [str(datetime.now())]

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


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
            filename = f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'

        elif scrape_type == "article":
            folder_structure = "Article"
            filename = f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'

        if not os.path.exists(folder_structure):
            os.makedirs(folder_structure)

        with open(f"{folder_structure}/{filename}", "w", encoding="utf-8") as file:
            json.dump(file_data, file, indent=4, ensure_ascii=False)

    except Exception as exception:
        LOGGER.info(f"Error occurred while writing json file {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error occurred while writing json file {str(exception)}"
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
        response = response.css('script[type="application/ld+json"]::text').getall()
        json_loads = json.loads(response[0])
        data = []

        if "publisher" in json_loads.keys():
            data.append(json_loads.get("publisher"))
            return data

    except Exception as exception:
        LOGGER.info(f"Error while fetching publisher data {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching publisher data {str(exception)}"
        )


def get_author(response) -> list:
    """
    The get_author function extracts information about the author(s)
    of an article from the given response object and
    returns it in the form of a list of dictionaries.
    Parameters:
        response (scrapy.http.Response): The response object containing
        the HTML of the article page.
    Returns:
        A list of dictionaries, where each dictionary contains information about one author.
    """
    try:
        parsed_data = response.css('script[type="application/ld+json"]::text').getall()
        json_loads = json.loads(parsed_data[0])

        author_data = []
        if json_loads.get("@type") == "NewsArticle":
            if "author" in json_loads.keys():
                author_data.append(json_loads.get("author"))
                return author_data[0]

    except Exception as exception:
        LOGGER.info(f"Error while fetching author {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching author {str(exception)}"
        )


def get_thumbnail_image(response) -> list:
    """extracting thumbnail image from application+ld/json data in main function
    Args:
        response (obj): page_object
    Returns:
        list: list of thumbnail images
    """
    try:
        response = get_main(response)
        if "image" in response[0].keys():
            thumbnail_image = []
            thumbnail_image.append(response[0].get("image").get("url"))
            return thumbnail_image

    except Exception as exception:
        LOGGER.info(f"Error while fetching thumbnail image {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching thumbnail image {str(exception)}"
        )


def get_embed_video_link(response) -> list:
    """
    extracting all the videos available from article
    parameters:
        response: html response
    returns:
        a list of dictionary containing object type link and decryption
    """
    try:
        data = []
        video_link = response.css(
            "figure.story__media gdwc-video-component::attr(data-src)"
        ).get()
        data.append(video_link)
        return data
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article video link: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting article video link: {exception}"
        )
