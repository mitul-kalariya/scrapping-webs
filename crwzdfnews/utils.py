# Utility/helper functions
# utils.py

import os
import re
import json
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from crwzdfnews import exceptions
from crwzdfnews.constant import TODAYS_DATE, LOGGER


def create_log_file():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                        filename="logs.log", filemode="a", datefmt="%Y-%m-%d %H:%M:%S", )


def validate_sitemap_date_range(start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    try:
        if start_date and not end_date:
            raise exceptions.InvalidDateException("end_date must be specified if start_date is provided")
        if not start_date and end_date:
            raise exceptions.InvalidDateException("start_date must be specified if end_date is provided")

        if start_date and end_date and start_date > end_date:
            raise exceptions.InvalidDateException("start_date should not be later than end_date")

        if start_date and end_date and start_date == end_date:
            raise exceptions.InvalidDateException("start_date and end_date must not be the same")

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException("start_date should not be greater than today_date")

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
        data_dict = [value for value in (remove_empty_elements(value) for value in parsed_data_dict) if
                     not empty(value)]
    else:
        data_dict = {key: value for key, value in
                     ((key, remove_empty_elements(value)) for key, value in parsed_data_dict.items()) if
                     not empty(value)}
    return data_dict


def get_raw_response(response):
    raw_resopnse = {"content_type": "text/html; charset=utf-8", "content": response.css("html").get(), }
    return raw_resopnse


def get_parsed_json(response):
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
    """generate required data as response json and response data

    Args:
        response (obj): site response object

    Returns:
        dict: returns 2 dictionary parsed_json and parsed_data
    """
    try:
        pattern = r"[\r\n\t\</h2>\<h2>]+"
        main_dict = {}
        main_data = get_main(response)

        topline = main_data[0].get("description")
        main_dict["description"] = [topline]

        title = response.css("h2#main-content").get()
        if title:
            title = re.sub(pattern, "", title.split("</span>")[2]).strip()
            main_dict["title"] = [title]

        published_on = main_data[1].get("datePublished")
        main_dict["published_at"] = [published_on]

        modified_on = main_data[1].get("dateModified")
        main_dict["modified_at"] = [modified_on]

        author = main_data[1].get("author")
        if author:
            main_dict["author"] = [author]

        publisher = main_data[1].get("publisher")
        main_dict["publisher"] = [publisher]

        display_text = response.css("p::text").getall()
        main_dict["text"] = [" ".join([re.sub("[\r\n\t]+", "", x).strip() for x in display_text])]

        images = get_images(response)
        if images:
            try:
                response_images = images[1:]
                if response_images:
                    main_dict["images"] = response_images

                thumbnail_image = images[0].get("link")
                if thumbnail_image:
                    main_dict["thumbnail_image"] = [thumbnail_image]

            except BaseException as e:
                LOGGER.error(f"{e}")

        mapper = {"de": "German"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        video = get_embed_video_link(response)
        main_dict["embed_video_link"] = video.get("videos")

        return remove_empty_elements(main_dict)
    except BaseException as e:
        LOGGER.error(f"while scrapping parsed data {e}")
        raise exceptions.ArticleScrappingException(f"while scrapping parsed data :{e}")


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


def get_images(response, parsed_json=False) -> list:
    images = response.css("figure.content-image")
    pattern = r"[\r\n\t]"
    data = []
    for image in images:
        temp_dict = {}
        link = image.css("img::attr(data-src)").get()
        caption = image.css("figcaption::text").get()
        if parsed_json:
            if link:
                temp_dict["@type"] = "ImageObject"
                temp_dict["link"] = link
        else:
            if link:
                temp_dict["link"] = link
                if caption:
                    temp_dict["caption"] = re.sub(pattern, "", caption).strip()
        data.append(temp_dict)
    return data


def get_embed_video_link(response) -> list:
    options = Options()
    options.headless = True
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(response.url)
    time.sleep(5)
    data = {}
    try:
        banner_button = driver.find_element(By.XPATH, "//div[@class='banner-actions-container']//button")
        if banner_button:
            banner_button.click()
            time.sleep(5)
            video_button = driver.find_elements(By.XPATH,
                                                "//button[@class='start-screen-play-button-26tC6k zdfplayer-button zdfplayer-tooltip svelte-mmt6rm']", )
            if video_button:
                videos = []
                for i in video_button:
                    i.click()
                    time.sleep(5)
                    video = i.find_elements(By.XPATH,
                                            "//div[@class='zdfplayer-video-container svelte-jemki7']/video[@class='video-1QZyVO svelte-ljt583 visible-1ZzN48']")[
                        -1].get_attribute("src").replace("blob:", "")
                    if video:
                        videos.append(video)
                data["videos"] = videos
    except Exception as e:
        LOGGER.error(f"Video not found in an article {e}")
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
        filename = (f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}')

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)
    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)
