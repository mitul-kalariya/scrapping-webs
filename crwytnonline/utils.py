"""Utility Functions"""
import json
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from crwytnonline import exceptions
from crwytnonline.constant import LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_raw_response(response):
    try:
        raw_resopnse = {
            "content_type": "text/html; charset=utf-8",
            "content": response.css("html").get(),
        }
        return raw_resopnse
    except BaseException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting raw response: {str(exception)}")


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
        ld_json_list = [get_ld_json(response)]

        for data in ld_json_list:
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
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting parsed json: {str(exception)}")


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
    except BaseException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting misc: {str(exception)}")


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

        json_data = get_ld_json(response)

        # Author
        authors = get_author(response)
        main_dict["author"] = authors

        # Last Updated Date
        last_updated_date = get_lastupdated(json_data)
        main_dict["modified_at"] = [last_updated_date]

        # Published Date
        published = get_published_at(json_data)
        main_dict["published_at"] = [published]

        # Description
        description = get_description(json_data)
        main_dict["description"] = [description]

        # Publisher
        publisher = get_publisher(json_data)
        main_dict["publisher"] = publisher

        # Article Text
        article_text = get_text(response)
        main_dict["text"] = [article_text]

        # Thumbnail
        thumbnail = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail

        # Title
        title = get_title(response)
        main_dict["title"] = [title]

        # Images
        article_images = get_images(response)
        main_dict["images"] = article_images

        # Videos
        video = get_embed_video_link(response)
        main_dict["embed_video_link"] = video

        # Language
        mapper = {"ko": "Korean"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        # Tags
        main_dict["tags"] = get_tags(response)

        # Section/Category
        main_dict["section"] = get_section(response)

        return remove_empty_elements(main_dict)
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article data (utils --> get_parsed_data): {str(exception)}")


def get_lastupdated(json_data) -> str:
    """
    This function extracts the last updated date and time of an article from a given Scrapy response object.
    It returns a string representation of the date and time in ISO 8601 format.
    If the information is not available in the response, it returns None.
    Args:
        response: A Scrapy response object representing the web page from which to extract the information.
    """
    try:
        last_updated = json_data.get("dateModified")
        return last_updated
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting last updated date: {str(exception)}")


def get_published_at(json_data) -> str:
    """get data of when article was published
    Args:
        response (object):page data
    Returns:
        str: datetime of published date
    """
    try:
        published_at = json_data.get("datePublished")
        return published_at
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting published date: {str(exception)}")


def get_description(json_data) -> list:
    """get article description
    Args:
        response (object):page data
    Returns:
        str: datetime of published date
    """
    try:
        description = json_data.get("description")
        return description
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article description: {str(exception)}")


def get_text(response) -> str:
    """get article text
    Args:
        response (object):page data
    Returns:
        str: datetime of published date
    """
    try:
        article_text = response.css(
            ".subhead::text , #CmAdContent span::text"
        ).getall()
        text = " ".join(article_text)
        return text
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article text: {str(exception)}")


def get_title(response) -> str:
    """get article title
    Args:
        response (object):page data
    Returns:
        str: datetime of published date
    """
    try:
        title = response.css(".top h3::text").get()
        if isinstance(title, str):
            title.strip()
        return title
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article title: {str(exception)}")


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
        authors = response.css(".articletag-author")
        temp_dict = {}
        if authors:
            data = [dict((("@type", "Person"), ("name", author.css("::text").get()),
                         ("url", f'https:{author.attrib.get("href")}'))) for author in authors]
        else:
            json_data = get_ld_json(response)

            data = []
            publisher_data = json_data.get("author")
            temp_dict["@type"] = publisher_data.get("@type")
            temp_dict["name"] = publisher_data.get("name")
            temp_dict["url"] = publisher_data.get("url")

            data.append(temp_dict)
        return data
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting author details: {str(exception)}")


def get_thumbnail_image(response) -> list:
    """
    Extracts information about the thumbnail image(s) associated with a webpage,
    including its link, width, and height, and returns the information as a list of dictionaries.
    Returns:
        A list of dictionaries, with each dictionary containing information about an image.
            If no images are found, an empty list is returned.
    """
    try:
        image_data = response.css(".imgArea img::attr(src)").get()
        return [image_data]
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting thumbnail image: {str(exception)}")


def get_embed_video_link(response) -> list:
    """
    A list of video objects containing information about the videos on the webpage.
    """
    try:
        options = Options()
        options.headless = True
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(response.url)

        video_links = []

        sel_video_links = driver.find_elements(By.XPATH, '//iframe[@id="zumFrame"]')
        iframes = driver.find_elements(By.CSS_SELECTOR, '.article p iframe')
        if sel_video_links:
            src = [link.get_attribute("src") for link in sel_video_links]
            video_links.extend(src)

        iframe_videos = [iframe.get_attribute("src") for iframe in iframes]
        if len(iframe_videos) > 0:
            if "youtube" in iframe_videos[0]:
                string_split = iframe_videos[0].split('?')[0]
                url_prefix = string_split.rsplit('/', 1)[1]
                youtube_video_link = 'https://www.youtube.com/watch?v=' + url_prefix
                video_links.append(youtube_video_link)
        return video_links
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting embed video links: {str(exception)}")
    finally:
        driver.quit()


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
        publisher_data = response.get("publisher")
        logo = publisher_data.get("logo")
        a_dict = {
            "@id": "ytn.co.kr",
            "@type": publisher_data.get("@type"),
            "name": publisher_data.get("name"),
            "logo": {
                "@type": logo.get("@type"),
                "url": logo.get("url"),
                "width": {
                    "@type": "Distance",
                    "name": str(logo.get("width")) + " px",
                },
                "height": {
                    "@type": "Distance",
                    "name": str(logo.get("height")) + " px",
                },
            },
        }
        return [a_dict]
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting publisher details: {str(exception)}")


def get_images(response) -> list:
    """
    Extracts all the images present in the web page.
    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    try:
        data = []
        images = response.css(".articledetail-image-left picture img")[1:]
        if images:
            for image in images:
                temp_dict = {}
                link = image.css('::attr(src)').get()
                alt_text = image.css("::attr(alt)").get()
                if link:
                    temp_dict["link"] = link
                if alt_text:
                    temp_dict["caption"] = alt_text
                data.append(temp_dict)
            return data
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article images: {str(exception)}")


def get_tags(response) -> list:
    """Extract all the tags available for the article
    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        list: List of tags
    """
    try:
        keyword_data = get_meta_information(response, property="keywords", key="name")
        tags = [data.strip() for data in keyword_data.split(",")]
        return tags
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article tags: {str(exception)}")


def get_section(response) -> list:
    """Extract all the sections/sub sections available for the article
    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        list: List of sections
    """
    try:
        sections = response.css('meta[property^="article:section"]::attr(content)').extract()
        return sections
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article sections: {str(exception)}")


def get_meta_information(response, property, key="property"):
    """Extract information from meta tag
    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
        property (str): meta property
    Returns:
        str: Requested meta tag content
    """
    try:
        if key == "property":
            meta_info = response.css(f'meta[property="{property}"]')
        else:
            meta_info = response.css(f'meta[{key}="{property}"]')
        if meta_info:
            meta_tag_text = meta_info.attrib["content"]
            return meta_tag_text
        return None
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting article details (meta info): {str(exception)}")


def get_ld_json(response) -> json:
    """Extract ld+json data
    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        json: ld+json data
    """
    try:
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()[0]
        json_data = json.loads(ld_json_data)
        return json_data
    except BaseException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while getting parsed json: {str(exception)}")


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param d: Input dictionary.
    :type d: dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
    :rtype: dict
    """
    try:
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
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while removing empty elements: {str(exception)}")
