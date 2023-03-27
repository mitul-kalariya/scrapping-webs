# Utility/helper functions
# utils.py

import os
import re
import json
import logging
import time
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from newton_scrapping import exceptions
from newton_scrapping.constants import TODAYS_DATE, BASE_URL, LOGGER


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
        datetime.strptime(
            start_date, "%Y-%m-%d").date() if start_date else None
    )
    end_date = (
        datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    )
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
    other_data = []
    ld_json_data = response.css(
        'script[type="application/ld+json"]::text').getall()
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
        misc = response.css(
            'script[type="application/ld+json"]::text').getall()
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

    response_data = {}
    pattern = r"[\r\n\t\"]+"
    embedded_video_links = []
    text = []
    main_json = get_main(response)

    article_title = response.css("h1.content_title::text").get()
    response_data["title"] = [re.sub(pattern, "", article_title).strip()]

    article_published = response.css(
        "div#content_scroll_start time::text").get()
    response_data["published_at"] = [article_published]

    article_description = response.css("div.chapo::text").get()
    response_data["description"] = [article_description]

    article_text = " ".join(response.css("p::text").getall())
    text.append(re.sub(pattern, "", article_text).strip())

    article_blockquote_text = " ".join(response.css("span::text").getall())
    text.append(re.sub(pattern, "", article_blockquote_text))

    response_data["text"] = [" ".join(text)]

    article_author = response.css("span.author_name::text").get()
    response_data["author"] = [
        {"@type": "Person",
            "name": re.sub(pattern, "", article_author).strip()}
    ]

    article_publisher = (main_json[1]).get("publisher")
    response_data["publisher"] = [article_publisher]

    article_thumbnail = (main_json[1]).get("image").get("contentUrl")
    if isinstance(article_thumbnail, list):
        response_data["thumbnail_image"] = article_thumbnail

    thumbnail_video = (main_json[1]).get("video").get("embedUrl")
    embedded_video_links.append(thumbnail_video)

    video_links = extract_videos(response)
    if video_links:
        for i in video_links.get("videos"):
            embedded_video_links.append(i)

    response_data["embed_video_link"] = embedded_video_links

    mapper = {"fr": "French"}
    article_lang = response.css("html::attr(lang)").get()
    response_data["source_language"] = [mapper.get(article_lang)]

 
    return remove_empty_elements(response_data)


def extract_videos(response) -> list:

    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    driver.get(response.url)
    time.sleep(3)
    banner_button = driver.find_element(
        By.XPATH, "//div[@class='multiple didomi-buttons didomi-popup-notice-buttons']//button[2]")
    if banner_button:
        banner_button.click()
        time.sleep(2)
        scroll = driver.find_elements(By.XPATH, "//p")
        for i in scroll:
            driver.execute_script(
                "window.scrollTo(" + str(i.location["x"]) + ", " + str(i.location["y"]) + ")")
        time.sleep(3)
        videos = driver.find_elements(
            By.XPATH, "//div[@class='video_block']//video-js//video[@class='vjs-tech']")
        if videos:
            data = {}
            for i in videos:
                try:
                    data["videos"] += [i.get_attribute(
                        "src").replace("blob:", "")]
                except:
                    data["videos"] = [i.get_attribute(
                        "src").replace("blob:", "")]
    driver.quit()
    return data


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
