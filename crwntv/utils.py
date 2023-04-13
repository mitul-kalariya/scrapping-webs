# Utility/helper functions
# utils.py

import re
import json
import logging
from crwntv import exceptions
from crwntv.constant import LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
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
        return remove_empty_elements(raw_resopnse)
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
    try:
        response_data = {}
        pattern = r"[\r\n\t\"]+"

        article_title = response.css("h2 span.article__headline::text").get()
        response_data["title"] = [re.sub(pattern, "", article_title).strip()]

        article_author = get_main(response)
        response_data['author'] = [article_author[0].get('author')]

        article_published = response.css("span.article__date::text").get()
        response_data["published_at"] = [article_published]

        article_modified = response.css('meta[name="last-modified"]::attr(content)').get()
        response_data["modified_at"] = [article_modified]

        article_description = response.css("p strong::text").get()
        response_data["description"] = [article_description]

        article_section = response.css("span[class=\"title title--dark\"]::text").get()
        if article_section:
            response_data["section"] = [article_section]

        article_publisher = get_main(response)
        response_data["publisher"] = [article_publisher[0].get("publisher")]

        article_text = " ".join(response.css("p::text").getall())
        if article_text:
            response_data["text"] = [article_text]
        elif response.css("div.article__text::text").get():
            response_data["text"] = [
                re.sub(pattern, "", response.css("div.article__text::text").get()).strip()
            ]

        article_thumbnail = get_thumbnail(response)
        response_data["thumbnail_image"] = article_thumbnail

        article_video = response.css("div.vplayer__video div video source::attr(src)").get()
        link = re.findall(r"http?.*?\.mp4", str(article_video))
        response_data["embed_video_link"] = link

        article_tags = response.css("section.article__tags ul li a::text").getall()
        response_data["tags"] = article_tags
        mapper = {"de": "German"}
        article_lang = response.css("html::attr(lang)").get()
        response_data["source_language"] = [mapper.get(article_lang)]

        return remove_empty_elements(response_data)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
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


def get_thumbnail(response) -> list:
    """extract thumbnail info from article

    Returns:
        list: target_data
    """
    try:
        video_article = response.css("div.vplayer div.vplayer__video")
        normal_article = response.css("div.article__media figure")
        data = []
        if normal_article:
            for i in normal_article:
                thumbnail_image = i.css("picture img::attr(src)").get()
                if thumbnail_image:
                    data.append(thumbnail_image)
        elif video_article:
            for j in video_article:
                thumbnail_image = j.css("img::attr(src)").get()
                if thumbnail_image:
                    data.append(thumbnail_image)
        return data

    except Exception as exception:
        LOGGER.info(f"Error while extracting thumbnail image: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting thumbnail image: {exception}"
        )
