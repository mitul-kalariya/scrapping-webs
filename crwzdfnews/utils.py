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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
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
            raise exceptions.InvalidDateException("end_date must be specified if start_date is provided")

        if not start_date and end_date:
            raise exceptions.InvalidDateException("start_date must be specified if end_date is provided")

        if start_date and end_date and start_date > end_date:
            raise exceptions.InvalidDateException("start_date should not be later than end_date")

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException("start_date should not be greater than today_date")

        if start_date and end_date and end_date > TODAYS_DATE:
            raise exceptions.InvalidDateException("start_date should not be greater than today_date")

    except exceptions.InvalidDateException as expception:
        LOGGER.info(
            f"Error occured while checking date range: {expception}"
        )
        raise exceptions.InvalidDateException(
            f"Error occured while checking date range: {expception}"
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
        data_dict = [value for value in (remove_empty_elements(value) for value in parsed_data_dict) if
                     not empty(value)]
    else:
        data_dict = {key: value for key, value in
                     ((key, remove_empty_elements(value)) for key, value in parsed_data_dict.items()) if
                     not empty(value)}
    return data_dict


def get_raw_response(response):
    raw_resopnse = {
        "content_type": "text/html; charset=utf-8",
        "content": response.css("html").get(),
    }
    return remove_empty_elements(raw_resopnse)


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
        ld_json_data = response.css(
            'script[type="application/ld+json"]::text').getall()
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
    
    except Exception as exception:
        LOGGER.info(f"Error while extracting tags: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting tags: {exception}"
        )


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
        article_json = main_data.get("article")
        videoobject_json = main_data.get("VideoObject")
        web_page = main_data.get("WebPage")
        if article_json:
            main_data = article_json
        else:
            main_data = videoobject_json

        description = main_data.get("description")
        main_dict["description"] = [description]

        if article_json:
            title = main_data.get("headline",None)
        else:
            title = main_data.get("name",None)
        main_dict["title"] = [title]


        if article_json:
            published_on = main_data.get("datePublished",None)
        else:
            published_on = main_data.get("uploadDate",None)
        main_dict["published_at"] = [published_on]

        modified_on = main_data.get("dateModified",None)
        main_dict["modified_at"] = [modified_on]

        author = main_data.get("author",None)
        main_dict["author"] = [author]

        section = get_section(response)
        main_dict["section"] = [section]

        publisher = main_data.get("publisher")
        main_dict["publisher"] = [publisher]

        display_text = response.css("p::text").getall()
        main_dict["text"] = [" ".join([re.sub("[\r\n\t]+", "", x).strip() for x in display_text])]

        images = get_images(response)
        main_dict["images"] = images

        thumbnail_image = web_page.get('thumbnailUrl')
        main_dict["thumbnail_image"] = [thumbnail_image]

        mapper = {"de": "German"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        video = get_embed_video_link(response)
        main_dict["embed_video_link"] = video.get("videos")

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_thumbnail_image(response):
    try:
        data = get_main(response)
        for data_block in data:
            if data_block.get('@type') == "WebPage":
                thumbnail = data_block.get('thumbnailUrl')
                if thumbnail:
                    return thumbnail

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting thumbnail image: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting thumbnail image: {exception}"
        )


def get_section(response):
    try:
        breadcrumb_list = response.css("div[class=\"breadcrumb-wrap grid-x\"] ol li a::text").getall()
        if breadcrumb_list[-1]:
            return breadcrumb_list[-1]

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting section: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting section: {exception}"
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

        information = {}
        main = response.css('script[type="application/ld+json"]::text').getall()
        for block in main:
            data = json.loads(block)
            if data.get("@type") == "NewsArticle":
                information["article"] = data
            elif data.get("@type") == "WebPage":
                information["WebPage"] = data
            elif data.get("@type") == "VideoObject":
                information["VideoObject"] = data
        return information
    except BaseException as exception:
        LOGGER.error("Error while getting main %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error while getting main: {exception}"
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


def get_images(response, parsed_json=False) -> list:
    try:
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

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article images: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting article images: {exception}"
        )


def get_embed_video_link(response) -> list:
    try:
        options = Options()
        options.headless = True
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(response.url)
        data = {}

        banner_button = driver.find_elements(By.XPATH, "//div[@class='banner-actions-container']//button")


        # banner_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
        #     By.XPATH, "//div[@class='banner-actions-container']//button")))
        breakpoint()
        if banner_button:
            banner_button.click()
            time.sleep(4)
            video_button = driver.find_elements(By.XPATH, "//button[@class='start-screen-play-button-26tC6k zdfplayer-button zdfplayer-tooltip svelte-mmt6rm']")

            # video_button = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((
            #     By.XPATH,
            #     "//button[@class='start-screen-play-button-26tC6k zdfplayer-button zdfplayer-tooltip svelte-mmt6rm']")))
            if video_button:
                videos = []
                for i in video_button:
                    i.click()
                    time.sleep(4)

                    video = driver.find_elements(By.XPATH, "//div[@class='zdfplayer-video-container svelte-jemki7']/video[@class='video-1QZyVO svelte-ljt583 visible-1ZzN48']")

                    # video = WebDriverWait(i, 10).until(EC.presence_of_all_elements_located((
                    #     By.XPATH,
                    #     "//div[@class='zdfplayer-video-container svelte-jemki7']/video[@class='video-1QZyVO svelte-ljt583 visible-1ZzN48']"
                    # )))
                    if video:
                        videos.append(video[-1].get_attribute("src").replace("blob:", ""))
                data["videos"] = videos
        else:
            driver.quit()

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting video links: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting video links: {exception}"
        )

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
    try:
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

    except Exception as exception:
            LOGGER.info(f"Error occurred while writing json file {str(exception)}")
            raise exceptions.ArticleScrappingException(
            f"Error occurred while writing json file {str(exception)}"
            )
