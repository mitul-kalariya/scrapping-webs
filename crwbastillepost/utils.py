# Utility/helper functions
# utils.py

import os
import re
import json
import logging
import requests
from io import BytesIO
from PIL import Image
from datetime import datetime
from crwbastillepost import exceptions
from crwbastillepost.constant import TODAYS_DATE, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def validate_sitemap_date_range(start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
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

        if start_date and end_date and start_date == end_date:
            raise exceptions.InvalidDateException(
                "start_date and end_date must not be the same"
            )

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "start_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as e:
        LOGGER.error(f"Error in __init__: {e}", exc_info=True)
        raise exceptions.InvalidDateException(f"Error in __init__: {e}")

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
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error while getting misc: {e}")

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
        # pattern = r"[\r\n\t\"]+"
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

    except BaseException as e:
        LOGGER.error(f"{e}")
        raise exceptions.ArticleScrappingException(f"Error while fetching parsed_data data: {e}")



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
    folder_structure = ""
    if scrape_type == "sitemap":
        folder_structure = "Links"
        filename = (
            f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )

    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)

    with open(f"{folder_structure}/{filename}", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)


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
        "video": None,
    }


# def get_parsed_data(response: str, parsed_json_main: list) -> dict:
#     """
#      Parsed data response from generated data using given response and selector

#     Args:
#         response: provided response
#         parsed_json_main: A list of dictionary with applications/+ld data

#     Returns:
#         Dictionary with Parsed json response from generated data
#     """
#     parsed_data_dict = get_parsed_data_dict()

#     parsed_data_dict |= get_country_details(parsed_json_main.getall())
#     parsed_data_dict |= get_language_details(parsed_json_main.getall(), response)
#     parsed_data_dict |= get_author_details(parsed_json_main.getall(), response)
#     parsed_data_dict |= get_descriptions_date_details(
#         parsed_json_main.getall(), response
#     )
#     parsed_data_dict |= get_publihser_details(parsed_json_main.getall(), response)
#     parsed_data_dict |= get_text_title_section_details(
#         parsed_json_main.getall(), response
#     )
#     parsed_data_dict |= get_thumbnail_image_video(parsed_json_main.getall(), response)
#     return parsed_data_dict


# def get_country_details(parsed_data: list) -> dict:
#     """
#     Return country related details
#     Args:
#         parsed_data: response of application/ld+json data
#     Returns:
#         dict: country related details
#     """
#     return next(
#         (
#             {
#                 "source_country": [
#                     json.loads(block).get("address", None).get("addressRegion", None)
#                 ]
#             }
#             for block in parsed_data
#             if json.loads(block).get("address", None)
#         ),
#         {"source_country": ["China"]},
#     )


# def get_language_details(parsed_data: list, response: str) -> dict:
#     """
#     Return language related details
#     Args:
#         parsed_data: response of application/ld+json data
#         response: provided response
#     Returns:
#         dict: language related details
#     """
#     return next(
#         (
#             {
#                 "source_language": [
#                     json.loads(block)
#                     .get("contactPoint", None)
#                     .get("availableLanguage", None)
#                 ]
#             }
#             for block in parsed_data
#             if json.loads(block).get("contactPoint", None)
#         ),
#         {"source_language": [response.css("html::attr(lang)").get()]},
#     )


# def get_author_details(parsed_data: list, response: str) -> dict:
#     """
#     Return author related details
#     Args:
#         parsed_data: response of application/ld+json data
#         response: provided response
#     Returns:
#         dict: author related details
#     """
#     # breakpoint()
#     # for block in parsed_data:
#     #     if "NewsArticle" in json.loads(block).get("@type", [{}]):
#     #         var = {
#     #             "author": [
#     #                 {
#     #                     "@type": json.loads(block).get("author", [{}]).get("@type"),
#     #                     "name": json.loads(block).get("author", [{}]).get("name"),
#     #                     "url": json.loads(block)
#     #                     .get("author", [{}])
#     #                     .get("url", None),
#     #                 }
#     #             ]
#     #         }
#     # return var
#     #         type = json.loads(i).get("author", [{}]).get("@type")
#     #         name = json.loads(i).get("author", [{}]).get("name")
#     #         url = json.loads(i)
#     #         return type, name, url
#     #     else:
#     #         name =  response.css("#storycenterbyline>div>a::text").get()
#     #         url =  response.css("#storycenterbyline>div>a::attr(href)").get()
#     #         return name, url

#     return next(
#         (
#             {
#                 "author": [
#                     {
#                         "@type": json.loads(block).get("author", [{}]).get("@type"),
#                         "name": json.loads(block).get("author", [{}]).get("name"),
#                         "url": json.loads(block)
#                         .get("author", [{}])
#                         .get("url", None),
#                     }
#                 ]
#             }
#             for block in parsed_data
#             if "NewsArticle" in json.loads(block).get("@type", [{}])
#         ),
#         {
#             "author": [
#                 {
#                     "name": response.css("#storycenterbyline>div>a::text").get(),
#                     "url": response.css("#storycenterbyline>div>a::attr(href)").get(),
#                 }
#             ]
#         },
#     )


# def get_descriptions_date_details(parsed_data: list, response: str) -> dict:
#     """
#     Returns description, modified date, published date details
#     Args:
#         parsed_data: response of application/ld+json data
#     Returns:
#         dict: description, modified date, published date related details
#     """
#     return next(
#         (
#             {
#                 "description": [json.loads(block).get("description")],
#                 "modified_at": [json.loads(block).get("dateModified")],
#                 "published_at": [json.loads(block).get("datePublished")],
#             }
#             for block in parsed_data
#             if "NewsArticle" in json.loads(block).get("@type")
#         ),
#         {
#             "description": response.css("h2.synopsis::text").getall(),
#             "modified_at": response.css("div.editor-date-logo div span::text").getall()
#                            or response.css("span.updated-date::attr(content)").getall(),
#             "published_at": response.css("div.ie-first-publish span::text").getall(),
#         },
#     )


# def get_publihser_details(parsed_data: list, response: str) -> dict:
#     """
#     Returns publisher details like name, type, id
#     Args:
#         parsed_data: response of application/ld+json data
#         response: provided response
#     Returns:
#         dict: publisher details like name, type, id related details
#     """
#     for block in parsed_data:
#         # breakpoint()
#         if "NewsArticle" in json.loads(block).get("@type"):
#             return {
#                 "publisher": [
#                     {
#                         "@id": json.loads(block)
#                         .get("publisher", None)
#                         .get("url", None),
#                         "@type": json.loads(block)
#                         .get("publisher", None)
#                         .get("@type", None),
#                         "name": response.css(
#                             "#wrapper div.main-header__logo img::attr(title)"
#                         ).get(),
#                         "logo": {
#                             "type": "ImageObject",
#                             "url": response.css(
#                                 "#wrapper div.main-header__logo img::attr(src)"
#                             ).get(),
#                             "width": {
#                                 "type": "Distance",
#                                 "name": response.css(
#                                     "#wrapper div.main-header__logo img::attr(width)"
#                                     ).get() + "px"if response.css(
#                                     "#wrapper div.main-header__logo img::attr(width)"
#                                 ).get() else None

#                             },
#                             # "height": {
#                             #     "type": "Distance",
#                             #     "name": response.css(
#                             #         "#wrapper div.main-header__logo img::attr(height)"
#                             #     , None).get()
#                             #             + "px",
#                             # },
#                         },
#                     }
#                 ]
#             }
#     return {
#         "publisher": [
#             {
#                 "name": response.css(
#                     "#wrapper div.main-header__logo img::attr(title)"
#                 ).get(),
#                 "logo": {
#                     "type": "ImageObject",
#                     "url": response.css(
#                         "#wrapper div.main-header__logo img::attr(src)"
#                     ).get(),
#                     "width": {
#                         "type": "Distance",
#                         "name": response.css(
#                             "#wrapper div.main-header__logo img::attr(width)"
#                         ).get()
#                                 + "px",
#                     },
#                     # "height": {
#                     #     "type": "Distance",
#                     #     "name": response.css(
#                     #         "#wrapper div.main-header__logo img::attr(height)"
#                     #     ).get()
#                     #             + "px",
#                     # },
#                 },
#             }
#         ]
#     }


# def get_text_title_section_details(parsed_data: list, response: str) -> dict:
#     """
#     Returns text, title, section details
#     Args:
#         parsed_data: response of application/ld+json data
#         response: provided response
#     Returns:
#         dict: text, title, section details
#     """
#     breakpoint()
#     for block in parsed_data:
#         if "NewsArticle" in json.loads(block).get("@type"):
#             return {
#                 # "title": response.css("h1.cat-theme-color::text").getall(),
#                 # "text": ["".join(json.loads(block).get("articleBody", []))],
#                 # "section": response.css(".single-article p::text").getall(),

#                 "title": response.css("h1.cat-theme-color::text").getall(),
#                 "text": response.css(".single-article p::text").getall(),
#                 "section": json.loads(block).get("articleSection"),
#             }
#     return {
#         "title": response.css("h1.cat-theme-color::text").getall(),
#         "section": response.css(".single-article p::text").getall(),
#     }


# def get_thumbnail_image_video(parsed_data: list, response: str) -> dict:
#     """
#     Returns thumbnail images, images and video details
#     Args:
#         parsed_data: response of application/ld+json data
#         response: provided response
#     Returns:
#         dict: thumbnail images, images and video details
#     """
#     thumbnail_url = None
#     breakpoint()
#     for block in parsed_data:
#         if json.loads(block).get("thumbnailUrl", None):
#             thumbnail_url = json.loads(block).get("thumbnailUrl")

#     return {
#         "images": [
#             {"link": img, "caption": cap}
#             for img, cap in itertools.zip_longest(
#                 response.css(".wp-caption a::attr(href)").getall(),
#                 response.css(".wp-caption-text::text").getall()
#                 + response.css("span.custom-caption::text").getall(),
#                 fillvalue=None,
#             )
#         ],
#         "video": [
#             {
#                 "link": response.css("span.embed-youtube iframe::attr(src)").getall(),
#             }
#         ],
#         "thumbnail_image": [thumbnail_url],
#     }
