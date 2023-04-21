# Utility/helper functions
# utils.py

import re
import json
import logging
import requests
import scrapy
from io import BytesIO
from PIL import Image
from datetime import datetime
from crwglobalnews.exceptions import ArticleScrappingException
from crwglobalnews.constant import LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param: parsed_data_dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
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


def get_raw_response(response: scrapy):
    raw_resopnse = {
        "content_type": "text/html; charset=utf-8",
        "content": response.css("html").get(),
    }
    return remove_empty_elements(raw_resopnse)


def get_parsed_json(response: scrapy):
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
        LOGGER.info(f"Error occurred while getting parsed json {exception}")
        raise ArticleScrappingException(
            f"Error occurred while getting parsed json {exception}"
        )


def get_main(response: scrapy):
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
        LOGGER.info(f"Error occurred while getting main: {exception}")
        raise ArticleScrappingException(
            f"Error occurred while getting main: {exception}"
        )


def get_misc(response: scrapy):
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
        LOGGER.info(f"Error occurred while getting misc: {exception}")
        raise ArticleScrappingException(
            f"Error occurred while getting misc: {exception}"
        )


def get_parsed_data(response: scrapy):
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
        pattern = r"[\r\n\t\"]+"
        publisher = get_publisher(response)
        main_dict["publisher"] = publisher

        article_label = response.css("div#article-label a::text").get()
        main_dict["category"] = [re.sub(pattern, "", article_label).strip()]

        headline = response.css("h1.l-article__title::text").getall()
        main_dict["title"] = headline
        authors = get_author(response)
        main_dict["author"] = authors

        main_data = get_main(response)
        main_dict["description"] = [main_data[0].get("description")]

        published_on = response.css(
            "div.c-byline__datesWrapper > div > div.c-byline__date--pubDate > span::text"
        ).get()
        published_on = published_on.strip("Posted ")
        main_dict["published_at"] = [published_on]
        main_dict["modified_at"] = [main_data[0].get("dateModified")]

        thumbnail_image = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail_image

        article_text = response.css("p::text").getall()
        main_dict["text"] = [" ".join(article_text)]

        tags = get_tags(response)
        main_dict["tags"] = tags

        section = response.css("div.l-article__label a::text").getall()
        section = re.sub(pattern, "", section[0]).strip()
        main_dict["section"] = [section]

        images = get_images(response)
        if images:
            main_dict["images"] = images

        videos = get_embed_video_link(response)
        main_dict["embed_video_link"] = videos

        mapper = {"en-US": "English"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        main_dict["source_country"] = ["Canada"]
        main_dict["time_scraped"] = [str(datetime.now())]

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_publisher(response: scrapy):
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
            "@id": "globalnews.ca",
            "@type": "NewsMediaOrganization",
            "name": "Global NEWS",
            "logo": {
                "@type": "ImageObject",
                "url": logo,
                "width": {"@type": "Distance", "name": str(width) + " px"},
                "height": {"@type": "Distance", "name": str(height) + " px"},
            },
        }
        a_dict = remove_empty_elements(a_dict)
        return [a_dict]

    except Exception as exception:
        LOGGER.info(f"Error while extracting publisher: {exception}")
        raise ArticleScrappingException(
            f"Error while extracting publisher: {exception}"
        )


def get_author(response: scrapy) -> list:
    """
    The get_author function extracts information about the author(s)
    of an article from the given response object and returns it in the form of a list of dictionaries.
    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        A list of dictionaries, where each dictionary contains information about one author.
    """
    try:
        info = response.css("div#article-byline")
        pattern = r"[\r\n\t\"]+"
        data = []
        if info:
            for author_block in info:
                temp_dict = {}
                temp_dict["@type"] = "Person"
                name = author_block.css("div.c-byline__attribution span a::text").get()
                if name:
                    name = re.sub(pattern, "", name).strip()
                    temp_dict["name"] = name.strip("By")

                else:
                    temp_dict["name"] = "Staff"

                link = author_block.css("div.c-byline__attribution span a::attr(href)").get()
                if link:
                    temp_dict["url"] = link
                """while reviewing if you feel that this data can be useful please uncomment it
                    it states from which organization the author is"""

                data.append(temp_dict)
            return data

    except Exception as exception:
        LOGGER.info(f"Error while extracting author name: {exception}")
        raise ArticleScrappingException(
            f"Error while extracting author name: {exception}"
        )


def get_thumbnail_image(response: scrapy) -> list:
    """extracting thumbnail image from application+ld/json data in main function
    Args:
        response (obj): page_object
    Returns:
        list: list of thumbnail images
    """
    try:
        image = get_main(response)
        thumbnail_image = []
        thumbnail_image.append(image[0].get("thumbnailUrl"))
        return thumbnail_image

    except Exception as exception:
        LOGGER.info(f"Error while extracting thumbnail image: {exception}")
        raise ArticleScrappingException(
            f"Error while extracting thumbnail image: {exception}"
        )


def get_tags(response: scrapy) -> list:
    """
    Extracts lables associated to the news article in form of a list of dictionary
    containing name of the tag and the corrosponding link to the tag
    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        a list of dictionary with link and name combination
    """
    try:
        info = response.css("div.c-tags__body a")
        data = []
        for block in info:
            url = block.css("a::attr(href)").get()
            if url == "#":
                pass
            else:
                data.append(block.css("a::text").get())
        return data

    except Exception as exception:
        LOGGER.info(f"Error while extracting tags: {exception}")
        raise ArticleScrappingException(
            f"Error while extracting tags: {exception}"
        )


def get_images(response: scrapy) -> list:
    """extracting image links from provided response
    Args:
        response (_type_): html page object
    Returns:
        list: list of images inside the article
    """
    try:
        images = response.css("figure.c-figure--alignnone")
        pattern = r"[\r\n\t]+"
        data = []
        if images:
            for image in images:
                temp_dict = {}
                link = image.css("img::attr(data-src)").get()
                caption = image.css(
                    "figcaption.c-figure__caption.c-caption span::text"
                ).get()
                if link:
                    temp_dict["link"] = link
                    if caption:
                        temp_dict["caption"] = re.sub(pattern, "", caption).strip()
                    data.append(temp_dict)
            return data

    except BaseException as exception:
        LOGGER.info(f"Error occurred while getting article images: {exception}")
        raise ArticleScrappingException(
            f"Error occurred while getting article images: {exception}"
        )


def get_embed_video_link(response: scrapy) -> list:
    """
    extracting all the videos available from article
    parameters:
        response: html response
    returns:
        a list of dictionary containing object type link and decryption
    """
    try:
        data = []
        videos = response.css("div.c-video.c-videoPlay")
        for video in videos:
            link = video.css("div::attr(data-displayinline)").get()
            if link:
                data.append(link)
        return data

    except BaseException as exception:
        LOGGER.info(f"Error occurred while getting video links: {exception}")
        raise ArticleScrappingException(
            f"Error occurred while getting video links: {exception}"
        )
