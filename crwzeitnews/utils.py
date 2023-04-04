"""Utility Functions"""
import os
import re
import json
import requests
from io import BytesIO
from PIL import Image
import logging
from datetime import datetime
from crwzeitnews import exceptions
from crwzeitnews.constant import (SITEMAP_URL, TODAYS_DATE, BASE_URL, LOGGER)
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_request_headers(url, type):
    headers = {}
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://www.zeit.de/index")
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/article/div/section[2]/div[1]/div')))
        banner_button = driver.find_element(By.XPATH, '//*[@id="main"]/div/article/div/section[2]/div[1]/div')
        if element:
            banner_button.click()
            article = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[3]')))
            if article:
                for request in driver.requests:
                    if "https://www.zeit.de/index" in str(request.url) and "cookie:" in str(request.headers):
                        headers |= format_headers(str(request.headers))
                        return headers

    except BaseException:
        pass


def format_headers(request_headers, sep=': ', strip_cookie=False, strip_cl=True,
                               strip_headers: list = []) -> dict:
    """
    formates a string of headers to a dictionary containing key-value pairs of request headers
    :param request_headers:
    :param sep:
    :param strip_cookie:
    :param strip_cl:
    :param strip_headers:
    :return: -> dictionary
    """
    headers_dict = dict()
    for keyvalue in request_headers.split('\n'):
        keyvalue = keyvalue.strip()
        if keyvalue and sep in keyvalue:
            value = ''
            key = keyvalue.split(sep)[0]
            if len(keyvalue.split(sep)) == 1:
                value = ''
            else:
                value = keyvalue.split(sep)[1]
            if value == '\'\'':
                value = ''
            if strip_cookie and key.lower() == 'cookie': continue
            if strip_cl and key.lower() == 'content-length': continue
            if key in strip_headers: continue
            headers_dict[key] = value

    headers_dict["cookie"] = parse_cookies(headers_dict.get("cookie",None))
    return headers_dict
def parse_cookies(self, raw_cookies):
    # parsed cookies
    cookies = {}

    # loop over cookies
    for cookie in raw_cookies.split('; '):
        try:
            # init cookie key
            key = cookie.split('=')[0]

            # init cookie value
            val = cookie.split('=')[1]

            # parse raw cookie string
            cookies[key] = val

        except:
            pass

    return cookies



def validate_sitemap_date_range(since, until):
    since = (
        datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
    )
    until = datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
    try:
        if (since and not until) or (not since and until):
            raise exceptions.InvalidDateException(
                "since or until must be specified"
            )

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

def export_data_to_json_file():
    pass


def get_raw_response():
    pass


def get_parsed_data():
    pass


def get_parsed_json():
    pass


"""
common function 
"""


def create_log_file():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                        filename="logs.log", filemode="a", datefmt="%Y-%m-%d %H:%M:%S", )


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
