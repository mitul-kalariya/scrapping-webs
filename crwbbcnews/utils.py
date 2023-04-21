"""Utility Functions"""
import json
import logging
import re
from datetime import datetime

import requests
from scrapy.loader import ItemLoader

from crwbbcnews.constant import BASE_URL, LOGGER, TODAYS_DATE
from crwbbcnews.exceptions import (ArticleScrappingException,
                                   InvalidDateException)
from crwbbcnews.items import ArticleRawParsedJson, ArticleRawResponse


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_date_range(since, until):
    """validated date range given by user
    Args:
        since (str): since
        until (str): until
    """
    since = datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
    until = datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
    try:
        if (since and not until) or (not since and until):
            raise InvalidDateException(
                "since or until must be specified"
            )

        if since and until and since > until:
            raise InvalidDateException(
                "since should not be later than until"
            )

        if since > TODAYS_DATE or until > TODAYS_DATE:
            raise InvalidDateException(
                "since and until should not be greater than today's date"
            )

    except InvalidDateException as expception:
        LOGGER.info(f"Error occured while checking date range: {expception}")
        raise InvalidDateException(
            f"Error occured while checking date range: {expception}"
        )


def get_raw_response(response: str, selector_and_key: dict) -> dict:
    """
    Raw response data generated from given response and selector

    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector

    Returns:
        Dictionary with generated raw response
    """
    try:
        article_raw_response_loader = ItemLoader(
            item=ArticleRawResponse(), response=response
        )
        for key, value in selector_and_key.items():
            article_raw_response_loader.add_value(key, value)
        return dict(article_raw_response_loader.load_item())
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting raw response: {exception}")
        raise ArticleScrappingException(
            f"Error occured while getting raw response: {exception}"
        )


def get_parsed_json(response: str, selector_and_key: dict) -> dict:  # noqa: C901
    """
     Parsed json response from generated data using given response and selector

    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector

    Returns:
        Dictionary with Parsed json response from generated data
    """
    try:
        article_raw_parsed_json_loader = ItemLoader(
            item=ArticleRawParsedJson(), response=response
        )
        for key, value in selector_and_key.items():

            if key == "main":
                article_raw_parsed_json_loader.add_value(
                    key,
                    [json.loads(data) if type(json.loads(data)) is dict else json.loads(
                        data)[0] for data in value.getall()
                     if (type(json.loads(data)) is dict and json.loads(data).get('@type') == "NewsArticle") or (
                        type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "NewsArticle") or (
                        type(json.loads(data)) in [list, dict])]

                )
            elif key == "imageObjects":
                article_raw_parsed_json_loader.add_value(
                    key, [json.loads(data) for data in value.getall() if
                          (type(json.loads(data)) is dict and json.loads(data).get(
                           '@type') in ["ImageGallery", "ImageObject"]) or (
                        type(json.loads(data)) is list and json.loads(data)[0].get(
                            '@type') in ["ImageGallery", "ImageObject"])]
                )

            elif key == "videoObjects":
                article_raw_parsed_json_loader.add_value(
                    key, [json.loads(data) for data in value.getall() if
                          (type(json.loads(data)) is dict and json.loads(data).get('@type') == "VideoObject") or (
                        type(json.loads(data)) is list and json.loads(data)[0].get('@type') == "VideoObject")]
                )
            elif key == "misc":
                article_raw_parsed_json_loader.add_value(
                    key, [json.loads(data) for data in value.getall()])
            else:
                for data in value.getall():
                    data_dict = json.loads(data)
                    graph_data = data_dict.get('@graph')
                    if graph_data and isinstance(graph_data, list):
                        data_type = graph_data[0].get('@type') or None
                    if data_dict is dict and data_type not in ["NewsArticle", "ImageGallery",
                                                               "ImageObject", "VideoObject"]:
                        article_raw_parsed_json_loader.add_value(key, data_dict)
        return dict(article_raw_parsed_json_loader.load_item())
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed json: {exception}")
        raise ArticleScrappingException(
            f"Error occured while getting parsed json: {exception}"
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
        "country": None,
        "language": None,
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
        "video": None,
    }


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param parsed_data_dict: Input dictionary.
    :type parsed_data_dict: dict
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


def get_data_from_json(response, parsed_main):
    """
    Get data from output response
    """
    try:
        url = response.url
        response_data = requests.get(f'{url}.json').json()
        parsed_json = {}
        raw_text = ''
        tags = []

        thumbnail_image = get_thumbnail_image(response)

        for block in response_data['content']['blocks']:
            if block['type'] == 'paragraph' or block['type'] == 'crosshead':
                raw_text = raw_text + f'{block["text"]}\n'

        for tag_block in response_data.get('metadata').get('tags').get('about'):
            tags.append(tag_block['topicName'])

        main_block = parsed_main.get("main").get("@graph")
        if main_block and isinstance(main_block, list) and len(main_block) > 0:
            author_data = main_block[0].get('author')

            author = [
                {
                    "@type": author_data.get("@type"),
                    "name": author_data.get("name")
                }
            ]

            parsed_json['author'] = author
            parsed_json['description'] = [main_block[0].get('description')]
            parsed_json['modified_at'] = [main_block[0].get('dateModified')]
            parsed_json['published_at'] = [main_block[0].get('datePublished')]

            publisher_data = main_block[0].get('publisher')
            publisher = [
                {
                    "@id": "bbc.com",
                    "@type": publisher_data.get("@type"),
                    "name": publisher_data.get("name"),
                    "logo": {
                        "@type": "ImageObject",
                        "url": publisher_data.get("logo").get("url"),
                        "width": {
                            "@type": "Distance",
                            "name": f"{publisher_data.get('logo').get('width')} px"
                        },
                        "height": {
                            "@type": "Distance",
                            "name": f"{publisher_data.get('logo').get('height')} px"
                        }
                    }
                }
            ]

            parsed_json['publisher'] = publisher

        promo_block = response_data.get("promo")
        if promo_block and isinstance(promo_block, dict):
            parsed_json['thumbnail_image'] = [promo_block.get('indexImage').get('href')]
            parsed_json['title'] = [promo_block.get('headlines').get('headline')]

        parsed_json['tags'] = tags
        parsed_json['text'] = [remove_html_tags(raw_text)]

        parsed_json['source_country'] = ['China']

        language_mapper = {
            "zh-hans": "Chinese"
        }
        language = response_data.get('metadata').get('passport').get('language')
        parsed_json['source_language'] = [language_mapper.get(str(language))]

        parsed_json['thumbnail_image'] = [thumbnail_image]
        parsed_json['images'] = get_images(response)
        parsed_json['embed_video_link'] = get_video(response)
        parsed_json["time_scraped"] = [str(datetime.now())]

        return remove_empty_elements(parsed_json)
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed data: {exception}")
        raise ArticleScrappingException(
            f"Error occured while getting parsed data: {exception}"
        )


def get_video(response) -> list:
    """Get video urls from the article

    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        list: list containing video urls
    """
    try:
        videos = response.css(".e1p6ccnx0")
        base_path = BASE_URL.split("/zhongwen/simp")
        base_url = base_path[0] if len(base_path) > 0 else None
        if base_url:
            video_links = [base_url + str(video.css("::attr(src)").get()) for video in videos]
            return video_links
        return None
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting video urls: {exception}")
        raise ArticleScrappingException(
            f"Error occured while getting video urls: {exception}"
        )


def get_thumbnail_image(response) -> list:
    """Get thumbnail image url

    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        list: list containing thumbnail image
    """
    try:
        thumbnail = response.css(".bbc-q4ibpr+ .ebmt73l0 .e1mo64ex0::attr(src)").get()
        return thumbnail
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting thumbnail image url: {exception}")
        raise ArticleScrappingException(
            f"Error occured while getting thumbnail image url: {exception}"
        )


def get_images(response) -> list:
    """Get url for all the images from the article

    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        list: list containing article images
    """
    try:
        data = []
        images = response.css(".bbc-172p16q")

        imgs = [img.css('img::attr(src)').get() for img in images]
        img_height = [img.css('img::attr(height)').get() for img in images]
        caps = [(img.css('figcaption p::text').get() or img.css('img::attr(alt)').get()) for img in images]

        data = [
            {
                "link": link,
                "caption": caption
            }
            for link, height, caption in zip(imgs, img_height, caps)
            if (isinstance(caption, str) and ("grey line" not in caption) and (int(height) > 2))
        ]
        return data
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article images urls: {exception}")
        raise ArticleScrappingException(
            f"Error occured while getting article images urls: {exception}"
        )


def remove_html_tags(text):
    """Remove HTML tags from text

    Args:
        text (str): Content with html tags

    Returns:
        str: Text after removing html tags
    """
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
