# Utility/helper functions
# utils.py
import os
import re
import json
import requests
from io import BytesIO
from PIL import Image
import logging
from datetime import datetime
from newton_scrapping import exceptions
from newton_scrapping.constant import TODAYS_DATE, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    """validated date range given by user

    Args:
        start_date (str): start_date
        end_date (str): end_date

    """
    start_date = (
        datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else TODAYS_DATE
    )
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else TODAYS_DATE
    try:
        if (start_date and not end_date) or (not start_date and end_date):
            raise exceptions.InvalidDateException(
                "start_date or end_date must be specified"
            )

        if start_date and end_date and start_date > end_date:
            raise exceptions.InvalidDateException(
                "start_date should not be later than end_date"
            )

        if start_date > TODAYS_DATE or end_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "start_date and end_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as e:
        LOGGER.error(f"Error in __init__: {e}", exc_info=True)
        raise exceptions.InvalidDateException(f"Error in __init__: {e}")


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

    except BaseException as e:
        exceptions.ArticleScrappingException(f"Error while parsing json data: {e}")
        LOGGER.error(f"Error while parsing json data: {e}")


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
        LOGGER.error(f"Error while getting misc{e}")
        exceptions.ArticleScrappingException(f"Error while getting misc {e}")


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
        exceptions.ArticleScrappingException(f"Error while getting misc: {e}")


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
        main_dict = {}
        main_data = get_main(response)
        for e in main_data:
            print("\n\n\n", e)
        authors = main_data[1].get("author")
        main_dict["author"] = authors
        last_updated = main_data[1].get("dateModified")
        main_dict["modified_at"] = [last_updated]
        published_on = main_data[1].get("datePublished")
        main_dict["published_at"] = [published_on]
        description = main_data[1].get("description")
        main_dict["description"] = [description]
        publisher = main_data[1].get("publisher")
        main_dict["publisher"] = publisher
        article_text = response.css("section p::text").getall()
        main_dict["text"] = [" ".join(article_text)]
        thumbnail = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail
        headline = response.css("h1.story-title::text").get().strip()
        main_dict["title"] = [headline]
        article_images = get_images(response)
        main_dict["images"] = article_images
        video = get_embed_video_link(response)
        main_dict["embed_video_link"] = video
        mapper = {"en": "English", "hi_IN": "Hindi"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        return remove_empty_elements(main_dict)

    except BaseException as e:
        LOGGER.error(f"{e}")
        exceptions.ArticleScrappingException(f"Error while fetching main data: {e}")


def get_lastupdated(response) -> str:
    """
    This function extracts the last updated date and time of an article from a given Scrapy response object.
    It returns a string representation of the date and time in ISO 8601 format.
    If the information is not available in the response, it returns None.

    Args:
        response: A Scrapy response object representing the web page from which to extract the information.
    """
    try:
        info = response.css("span.time-elapsed")
        if info:
            return info.css("time::attr(datetime)").get()
    except BaseException as e:
        LOGGER.error(f"error while getting last updated{e}")


def get_published_at(response) -> str:
    """get data of when article was published

    Args:
        response (object):page data

    Returns:
        str: datetime of published date
    """
    info = response.xpath('//div[@class ="padtop10 padbtm10"]')
    info_eng = response.css("div.padtop20")

    if info:
        return info.css("time::attr(datetime)").get()
    elif info_eng:
        return info_eng.css("time::attr(datetime)").get()


def get_author(response) -> list:
    """
    The extract_author function extracts information about the author(s)
    of an article from the given response object and returns it in the form of a list of dictionaries.

    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        A list of dictionaries, where each dictionary contains information about one author.

    """
    info = response.css("div.author")
    pattern = r"[\r\n\t\"]+"
    data = []
    if info:
        for i in info:
            temp_dict = {}
            temp_dict["@type"] = "Person"
            temp_dict["name"] = re.sub(
                pattern, "", i.css("div a span::text").get()
            ).strip()
            temp_dict["url"] = i.css("div a::attr(href)").get()
            data.append(temp_dict)
        return data


def get_thumbnail_image(response) -> list:
    """
    The function extract_thumbnail extracts information about the thumbnail image(s) associated with a webpage,
    including its link, width, and height, and returns the information as a list of dictionaries.

    Returns:
        A list of dictionaries, with each dictionary containing information about an image.
            If no images are found, an empty list is returned.
    """
    info = response.css("div.gallery-item")
    mod_info = response.css(".storypicture img.width100")
    data = []
    if info:
        for i in info:
            image = i.css("div.gallery-item-img-wrapper img::attr(src)").get()
            if image:
                data.append(image)
    elif mod_info:
        for i in mod_info:
            image = i.css("img::attr(src)").get()
            if image:
                data.append(image)
    return data


def get_embed_video_link(response) -> list:
    """
    A list of video objects containing information about the videos on the webpage.
    """
    info = response.css("div.videoWrapper")
    data = []
    if info:
        for i in info:
            js = i.css("script").get()
            request_link = re.findall(r"playlist\s*:\s*'(\S+)'", js)[0]
            response = requests.get(request_link)
            link = response.json().get("playlist")[0].get("sources")[1].get("file")
            temp_dict = {"link": link}
            data.append(temp_dict)
    return data


def get_publisher(response) -> list:
    """
    Extracts publisher information from the given response object and returns it as a dictionary.

    Returns:
    - A dictionary containing information about the publisher. The dictionary has the following keys:
        - "@id": The unique identifier for the publisher.
        - "@type": The type of publisher (in this case, always "NewsMediaOrganization").
        - "name": The name of the publisher.
    """
    logo = response.css('link[rel="icon"]::attr(href)').getall()[2]
    img_response = requests.get(logo)
    width, height = Image.open(BytesIO(img_response.content)).size
    a_dict = {
        "@id": "bharat.republicworld.com",
        "@type": "NewsMediaOrganization",
        "name": "Bharat republic word",
        "logo": {
            "@type": "ImageObject",
            "url": logo,
            "width": {"@type": "Distance", "name": str(width) + " px"},
            "height": {"@type": "Distance", "name": str(height) + " px"},
        },
    }
    return [a_dict]


def get_images(response) -> list:
    """
    Extracts all the images present in the web page.

    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    info = response.css("div.embedpicture")
    data = []
    if info:
        for i in info:
            temp_dict = {}
            image = i.css("div.embedimgblock img::attr(src)").get()
            if image:
                temp_dict["link"] = image
            data.append(temp_dict)
    return data


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
