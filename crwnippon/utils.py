# Utility/helper functions
# utils.py

import json
import logging
import os
import re
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from crwnippon import exceptions
from crwnippon.constant import BASE_URL, LOGGER, TODAYS_DATE


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(since, until):
    since = datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
    until = datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
    try:
        if (since and not until) or (not since and until):
            raise exceptions.InvalidDateException("since or until must be specified")

        if since and until and since > until:
            raise exceptions.InvalidDateException(
                "since should not be later than until"
            )

        if since > TODAYS_DATE or until > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "since and until should not be greater than today_date"
            )

        if since and until and since > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "since should not be greater than today_date"
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
    try:
        raw_resopnse = {
            "content_type": "text/html; charset=utf-8",
            "content": response.css("html").get(),
        }
        return raw_resopnse
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting raw response: {str(exception)}")


def get_parsed_json(response):
    # """
    # extracts json data from web page and returns a dictionary
    # Parameters:
    #     response(object): web page
    # Returns
    #     parsed_json(dictionary): available json data
    # """
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
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting parsed json: {str(exception)}")


def get_parsed_data(response):
    try:
        pattern = r"[\r\n\t\"]+"
        main_dict = {}
        # extract author info
        authors = get_author(response)
        main_dict["author"] = authors

        # extract main headline of article
        title = response.css(".c-h1::text").get()
        main_dict["title"] = [title]

        # main_dict["publisher"] = [main_data[0].get("publisher")]

        # extract the date published at
        published_time_meta = response.css('meta[property="article:published_time"]')
        published_time = published_time_meta.attrib["content"]
        main_dict["published_at"] = [published_time]
        published_time_meta = response.css('meta[property="article:modified_time"]')
        published_time = published_time_meta.attrib["content"]
        main_dict["modified_at"] = [published_time]
        description = response.css(".c-read::text").get()
        if description:
            main_dict["description"] = [re.sub(pattern, "", description)]
        publisher = get_publisher(response)
        main_dict["publisher"] = publisher
        text = response.css(
            ".editArea h2::text , .editArea p::text , .editArea font::text"
        ).getall()
        if text:
            main_dict["text"] = ["".join(list(filter(None, text)))]
        thumbnail_image = response.css(".c-detailmv::attr(src)").get()
        if thumbnail_image:
            main_dict["thumbnail_image"] = [BASE_URL[:-4] + thumbnail_image]
        article_images = get_images(response)
        main_dict["images"] = article_images
        frame_video = get_embed_video_link(response)
        main_dict["embed_video_link"] = frame_video
        tags = get_tags(response)
        main_dict["tags"] = tags
        mapper = {"ja": "Japanese"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]
        main_dict["section"] = get_section(response)

        return remove_empty_elements(main_dict)
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting parsed data: {str(exception)}")


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
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting main: {str(exception)}")


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
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting misc: {str(exception)}")


def get_embed_video_link(response) -> list:
    try:
        info = []
        videos = response.css("p.video iframe::attr(src)").getall()
        for video in videos:
            if video:
                info.append(video)
        return info
    except exceptions.URLNotFoundException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting embed video link: {str(exception)}")


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
        options = Options()
        options.headless = True
        driver = webdriver.Chrome(options=options)
        driver.get(response.url)
        data = []
        temp_dict = {}
        author_link = driver.find_elements(By.XPATH, '//a[@class="is-ttl"]')
        author_meta = response.css('meta[name="cXenseParse:author"]')
        if author_meta:
            author = author_meta.attrib["content"]
            temp_dict["@type"] = "Person"
            temp_dict["name"] = author
            temp_dict["link"] = author_link[0].get_attribute("href")

        data.append(temp_dict)
        return data
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting author information: {str(exception)}")


def get_tags(response) -> list:
    try:
        data = []
        news_tags = response.css(".c-keywords a::text").getall()
        for tag in news_tags:
            data.append(tag)
        return data
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting news tags: {str(exception)}")


def get_section(response) -> list:
    """Extract section (category) of the article

    Args:
        response (object): web page data

    Returns:
        list: list of sections
    """
    try:
        sections = response.css("meta[name='cXenseParse:ncf-category']")
        section_list = [section.attrib["content"] for section in sections]
        if len(section_list) > 0:
            return section_list
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article sections: {str(exception)}")


def get_images(response, parsed_json=False) -> list:
    """
    Extracts all the images present in the web page.
    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    try:
        data = []
        images = response.css(".fancybox img::attr(src), .copy_ng::attr(src)").getall()
        caption = response.css(".fancybox img::attr(alt), .copy_ng::attr(alt)").getall()
        if images:
            for image, caption in zip(images, caption):
                temp_dict = {}
                if image:
                    temp_dict["link"] = BASE_URL[:-4] + image
                    if caption:
                        temp_dict["caption"] = caption
                data.append(temp_dict)
            return data
    except exceptions.URLNotFoundException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting news content images: {str(exception)}")


def get_publisher(response) -> list:
    """
    Extracts publisher information from the given response object and returns it as a dictionary.
    Returns:
    - A dictionary containing information about the publisher. The dictionary has the following keys:
        - "@id": The unique identifier for the publisher.
        - "@type": The type of publisher (in this case, always "NewsMediaOrganization").
        - "name": The name of the publisher.
    """
    try:
        favicon_link = response.css('link[rel="shortcut icon"]::attr(href)').get()
        favicon_url = response.urljoin(favicon_link)
        img_response = requests.get(favicon_url)
        width, height = Image.open(BytesIO(img_response.content)).size
        a_dict = {
            "@id": "nippon.com",
            "@type": "Organization",
            "name": "nippon",
            "logo": {
                "@type": "ImageObject",
                "url": favicon_url,
                "width": {"@type": "Distance", "name": str(width) + " px"},
                "height": {"@type": "Distance", "name": str(height) + " px"},
            },
        }
        return [a_dict]
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting publisher information: {str(exception)}")


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
        json.dump(file_data, file, indent=4, ensure_ascii=False)
