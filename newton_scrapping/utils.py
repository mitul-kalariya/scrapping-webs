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
from newton_scrapping import exceptions
from newton_scrapping.constants import TODAYS_DATE, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
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


def get_raw_response(response):
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
    parsed_json = {}

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
            parsed_json["other"] = data

    misc = get_misc(response)
    if misc:
        parsed_json["misc"] = misc

    return remove_empty_elements(parsed_json)


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
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error while getting main: {e}")


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
        pattern = r"[\r\n\t\"]+"
        publisher = get_publisher(response)
        main_dict["publisher"] = publisher

        article_label = response.css("div#article-label a::text").get()
        main_dict["category"] = [re.sub(pattern, "", article_label).strip()]

        headline = response.css("h1.l-article__title::text").getall()
        main_dict["title"] = headline

        authors = get_author(response)
        main_dict["author"] = authors

        published_on = response.css(
            "div.c-byline__datesWrapper > div > div.c-byline__date--pubDate > span::text"
        ).get()
        published_on = published_on.strip("Posted ")
        main_dict["published_at"] = [published_on]

        updated_on = response.css(
            "div.c-byline__datesWrapper > div > div.c-byline__date--modDate > span::text"
        ).get()
        main_dict["modified_at"] = [updated_on]

        thumbnail_image = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail_image

        article_text = response.css("p::text").getall()
        main_dict["text"] = [" ".join(article_text)]

        tags = get_tags(response)
        main_dict["tags"] = tags

        images = get_images(response)
        main_dict["images"] = images

        videos = get_embed_video_link(response)
        main_dict["embed_video_link"] = videos

        mapper = {"en-US": "English"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["language"] = [mapper.get(article_lang)]

        return remove_empty_elements(main_dict)
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error: {e}")


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
        return [a_dict]
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error: {e}")


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
        info = response.css("div#article-byline")
        pattern = r"[\r\n\t\"]+"
        data = []
        if info:
            for i in info:
                temp_dict = {}
                temp_dict["@type"] = "Person"
                name = i.css("div.c-byline__attribution span a::text").get()
                if name:
                    name = re.sub(pattern, "", name).strip()
                    temp_dict["name"] = name.strip("By")

                else:
                    temp_dict["name"] = "Staff"

                link = i.css("div.c-byline__attribution span a::attr(href)").get()
                if link:
                    temp_dict["url"] = link
                """while reviewing if you feel that this data can be useful please uncomment it
                    it states from which organization the author is"""

                data.append(temp_dict)
            return data
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error: {e}")


def get_thumbnail_image(response) -> list:
    """extracting thumbnail image from application+ld/json data in main function
    Args:
        response (obj): page_object
    Returns:
        list: list of thumbnail images
    """
    image = get_main(response)
    thumbnail_image = []
    thumbnail_image.append(image[0].get("thumbnailUrl"))
    return thumbnail_image


def get_tags(response) -> list:
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
        for i in info:
            temp_dict = {}
            temp_dict["tag"] = i.css("a::text").get()
            temp_dict["url"] = i.css("a::attr(href)").get()
            if temp_dict["url"] == "#":
                pass
            else:
                data.append(temp_dict)
        return data
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error: {e}")


def get_images(response) -> list:
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
                    temp_dict["url"] = link
                    if caption:
                        temp_dict["caption"] = re.sub(pattern, "", caption).strip()
                    data.append(temp_dict)
            return data
    except BaseException as e:
        LOGGER.error(f"Error: {e}")
        print(f"Error: {e}")


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
        thumbnail_video = response.css("figure.l-article__featured")
        for video in thumbnail_video:
            link = video.css(".c-video::attr(data-displayinline)").get()
            if link:
                data.append(link)

        videos = response.css("div.c-video.c-videoPlay")
        for video in videos:
            link = video.css("div::attr(data-displayinline)").get()
            if link:
                data.append(link)
        return data
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error: {e}")



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
        filename = f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)
    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)
