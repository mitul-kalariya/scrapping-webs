"""Utility Functions"""
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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from crwterra import exceptions
from crwterra.constant import TODAYS_DATE, LOGGER



def create_log_file():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
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

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException("start_date should not be greater than today_date")

        if start_date and end_date and end_date > TODAYS_DATE:
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

        return remove_empty_elements(parsed_json)
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed json {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting parsed json {exception}"
        ) from exception


def get_parsed_data(response):
    """generate required data as response json and response data

    Args:
        response (obj): site response object

    Returns:
        dict: returns 2 dictionary parsed_json and parsed_data
    """
    try:
        pattern = r"[\r\n\t]+"
        main_dict = {}
        main_data = get_main(response)

        author = main_data[0].get("author")
        if author:
            main_dict["author"] = author
    

        topline = main_data[0].get("description")
        main_dict["description"] = [topline]

        modified_on = main_data[0].get("dateModified")
        main_dict["modified_at"] = [modified_on]

        published_on = main_data[0].get("datePublished")
        main_dict["published_at"] = [published_on]

        publisher = main_data[0].get("publisher")
        main_dict["publisher"] = [publisher]

        main_dict["text"] = get_text(response)

        main_dict["thumbnail_image"] = get_thumbnail_image(response)
        
        title = main_data[0].get("headline")
        main_dict["title"] = [title]

        main_dict["images"] = get_images(response)

        if main_data[0].get("@type") == "VideoObject":
            main_dict["embed_video_link"]  = extract_videos(response)

        main_dict["section"] = get_section(response)
      
        mapper = {"pt-BR": "Portuguese"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]


        return remove_empty_elements(main_dict)
    except BaseException as e:
        LOGGER.error(f"while scrapping parsed data {e}")
        raise exceptions.ArticleScrappingException(f"while scrapping parsed data :{e}")


def get_section(response):
    section = response.css("ul.breadcrumb li a::text").getall()
    if section:
        temp_list = [re.sub(r"[\n\r\t]","",i).strip() for i in section]
        breadcrumb = [i for i in temp_list if i]
        return [breadcrumb[len(breadcrumb)-1]]

def get_text(response):
    """
    extracts text data from web page and returns a dictionary
    Parameters:
        response(object): web page
    Returns
        parsed_json(dictionary): available json data
    """
    try:
        video_link_text = response.css("div.article__content--container p::text").get()
        if video_link_text:
            return [video_link_text]
        
        text = response.css("p.text::text").getall()
        if text:
            strong_text = response.css("p.text strong::text").get()
            if strong_text:
                return [strong_text +" ".join([re.sub("[\r\n\t]+", "", x).strip() for x in text])]
            else:
                return [" ".join([re.sub("[\r\n\t]+", "", x).strip() for x in text])]
    
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed json {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting parsed json {exception}"
        ) from exception


def get_thumbnail_image(response):
    main_data = get_main(response)
    try:
        thumbnail_url = main_data[0].get("thumbnailUrl")
        if thumbnail_url:
            return [thumbnail_url]
        image = main_data[0].get("image")[0]
        if image:
            return [image]
    except:
        pass

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
        LOGGER.error(f"error parsing ld+json main data{e}")
        raise exceptions.ArticleScrappingException(f"error parsing ld+json main data {e}")

def get_images(response):
    images = response.css("div.article__content--body.article__content--internal figure[itemprop='associatedMedia image'] meta[itemprop='url']::attr(content)").getall()
    image_caption = response.css("div.article__content--body.article__content--internal figure[itemprop='associatedMedia image'] picture img::attr(alt)").getall()
    image_list = []
    for i in range(0,len(images)):
        image_dict = {}
        image_dict['link'] = images[i]
        image_dict['caption'] = image_caption[i]
        image_list.append(image_dict)
    if image_list:
        return image_list

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
    except BaseException as e:
        LOGGER.error(f"error while creating json file: {e}")
        raise exceptions.ExportOutputFileException(f"error while creating json file: {e}")


def extract_videos(response) -> list:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(response.url)

    try:
        video = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
            (By.XPATH, "//*[@id=\"zp-vjs-66d509e3f08baa2b5888e59805b04086o25a3fy8_html5_api\"]"))).get_attribute("src") or None
    except:
        return None

    driver.quit()
    if video:
        return [video]
