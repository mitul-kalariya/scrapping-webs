"""Utility Functions"""
import os
import json
import logging
import time
from datetime import datetime

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from seleniumwire import webdriver

from crwzeitnews import exceptions
from crwzeitnews.constant import TODAYS_DATE, LOGGER


def get_request_headers():
    """fetching headers from selenium instance

    Returns:
        dict: containing formatted request headers containing cookies
    """
    headers = {}
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://www.zeit.de/index")
    try:
        time.sleep(2)
        element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
               (By.CSS_SELECTOR,"div.option__accbtn")
            )
        )

        if element:
            time.sleep(2)
            element.click()
            time.sleep(2)
            article = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH , "/html/body/div[3]"))
            )
            if article:
                for request in driver.requests:
                    if "https://www.zeit.de/index" in str(
                        request.url
                    ) and "cookie:" in str(request.headers):
                        headers = format_headers(str(request.headers))
                        return headers
        return None

    except BaseException as exception:
        LOGGER.debug("error while running selenium instance: %s", exception)
        raise exceptions.RequestHeadersException(
            f"error while running selenium instance: {exception}"
        )


def format_headers(
    request_headers, sep=": ", strip_cookie=False, strip_cl=True, strip_headers=[]
) -> dict:
    """
    formates a string of headers to a dictionary containing key-value pairs of request headers
    :param request_headers:
    :param sep:
    :param strip_cookie:
    :param strip_cl:
    :param strip_headers:
    :return: -> dictionary
    """
    try:
        headers_dict = {}
        for keyvalue in request_headers.split("\n"):
            keyvalue = keyvalue.strip()
            if keyvalue and sep in keyvalue:
                value = ""
                key = keyvalue.split(sep)[0]
                if len(keyvalue.split(sep)) == 1:
                    value = ""
                else:
                    value = keyvalue.split(sep)[1]
                if value == "''":
                    value = ""
                if strip_cookie and key.lower() == "cookie":
                    continue
                if strip_cl and key.lower() == "content-length":
                    continue
                if key in strip_headers:
                    continue
                headers_dict[key] = value

        headers_dict["cookie"] = parse_cookies(headers_dict.get("cookie", None))
        return headers_dict
    except BaseException as exception:
        LOGGER.debug("error while folding header data: %s ", exception)
        raise exceptions.RequestHeadersException(
            f"error while folding headers data: {exception}"
        )


def parse_cookies(raw_cookies):
    """parsing cookies from raw string"""
    cookies = {}

    # loop over cookies
    for cookie in raw_cookies.split("; "):
        try:
            # init cookie key
            key = cookie.split("=")[0]

            # init cookie value
            val = cookie.split("=")[1]

            # parse raw cookie string
            cookies[key] = val

        except BaseException as exception:
            LOGGER.debug("error while folding cookies data: %s", exception)
            raise exceptions.RequestHeadersException(
                f"error while folding cookies data: {exception}"
            )

    return cookies


def validate_sitemap_date_range(since, until):
    """
    validating date range given for sitemap
    """
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

    except exceptions.InvalidDateException as exception:
        LOGGER.error("Error in __init__: %s ", exception, exc_info=True)
        raise exceptions.InvalidDateException(f"Error in __init__: {exception}")


def create_log_file():
    """creating log file"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param d: Input dictionary.
    :type d: dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
    :rtype: dict
    """

    def empty(value):
        return value is None or value == {} or value == [] or value == ""

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
    """parsing raw response
    returns: raw response
    """
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
        image_objects = []
        video_objects = []
        other_data = []
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
        for a_block in ld_json_data:
            data = json.loads(a_block)
            if data.get("@type") == "Article":
                parsed_json["main"] = data
            elif data.get("@type") in {"ImageGallery", "ImageObject"}:
                image_objects.append(data)
            elif data.get("@type") == "VideoObject":
                video_objects.append(data)
            else:
                other_data.append(data)

        parsed_json["imageObjects"] = image_objects
        parsed_json["videoObjects"] = video_objects
        parsed_json["other"] = other_data
        misc = get_misc(response)
        if misc:
            parsed_json["misc"] = misc
        return remove_empty_elements(parsed_json)

    except BaseException as exception:
        LOGGER.info("Error occured while getting parsed json %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error occurred while getting parsed json {exception}"
        )


def get_publisher_info(article_data: dict) -> dict:
    """
    filtering required information from article data
    Parameters:
        article_data: dict
    returns: dict
    """
    return remove_empty_elements(
        {
            "@id": article_data.get("@id", None),
            "@type": article_data.get("@type", None),
            "name": article_data.get("name", None),
            "url": article_data.get("url", None),
            "logo": article_data.get("logo", None),
        }
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
            if data.get("@type") == "Article":
                information["article"] = data
            elif data.get("@type") == "WebPage":
                information["WebPage"] = data
            elif data.get("@type") == "VideoObject":
                information["VideoObject"] = data
            elif data.get("@type") in {"NewsMediaOrganization", "Organization"}:
                information["publisher_info"] = get_publisher_info(data)
            else:
                pass
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
        LOGGER.error("error while getting misc: %s ", exception)
        raise exceptions.ArticleScrappingException(
            f"Error while getting misc: {exception}"
        )


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
        "embed_video_link": None,
    }


def get_parsed_data(response: str) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """

    imp_ld_json_data = get_main(response)
    article_json = imp_ld_json_data.get("article")
    webpage_json = imp_ld_json_data.get("WebPage")
    publisher_info_json = imp_ld_json_data.get("publisher_info")
    videoobject_json = imp_ld_json_data.get("VideoObject")
    if article_json:
        parsed_json_main = article_json
    else:
        parsed_json_main = videoobject_json
    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= get_country_details()
    parsed_data_dict |= {"source_language": ["German"]}
    parsed_data_dict |= get_author_details(parsed_json_main, response)
    parsed_data_dict |= get_descriptions_date_details(parsed_json_main)
    parsed_data_dict |= get_publisher_details(publisher_info_json)
    parsed_data_dict |= get_text_title_section_tag_details(parsed_json_main, response)
    parsed_data_dict |= get_thumbnail_image_video(
        response, webpage_json, parsed_json_main
    )
    final_dict = format_dictionary(parsed_data_dict)
    return remove_empty_elements(final_dict)


def get_country_details() -> dict:
    """
    Return country related details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: country related details
    """

    return {"source_country": ["Germany"]}


def get_author_details(parsed_data: list, response: str) -> dict:
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: author related details
    """
    author_details = []
    parsed_data = format_dictionary(parsed_data)
    if not parsed_data.get("author"):
        return author_details.append(
            {
                "name": response.css(
                    'div.column-heading__name > script[itemprop="name"]::text'
                )
                .get()
                .strip()
            }
        )
    author_details.extend(
        {
            "@type": author.get("@type"),
            "name": author.get("name"),
            "url": author.get("url", None),
        }
        for author in parsed_data.get("author")
    )
    return {"author": author_details}


def get_descriptions_date_details(parsed_data: list) -> dict:
    """
    Returns description, modified date, published date details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: description, modified date, published date related details
    """
    if parsed_data.get("@type")[0] in {"Article", "VideoObject"}:
        return {
            "description": parsed_data.get("description"),
            "modified_at": parsed_data.get("dateModified"),
            "published_at": parsed_data.get("datePublished"),
        }

    return {
        "description": None,
        "modified_at": None,
        "published_at": None,
    }


def get_publisher_details(parsed_data: list) -> dict:
    """
    Returns publisher details like name, type, id
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: publisher details like name, type, id related details
    """
    return {"publisher": parsed_data}


def get_text_title_section_tag_details(parsed_data: list, response: str) -> dict:
    """
    Returns text, title, section details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: text, title, section, tag details
    """
    if parsed_data.get("@type")[0] in {"Article", "VideoObject"}:
        return {
            "title": parsed_data.get("headline"),
            "text": parsed_data.get("articleBody"),
            "section": parsed_data.get("articleSection"),
            "tags": parsed_data.get("keywords"),
        }
    return {
        "title": response.css("header.article-header > h1::text").getall(),
        "tags": response.css("ul.article-tags__list > li > a::text").getall(),
    }


def get_thumbnail_image_video(
    response: str, webpage_json: dict, parsed_data: dict
) -> dict:
    """
    Returns thumbnail images, images and video details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: thumbnail images, images and video details
    """
    video_urls = []
    thumbnail_url = []
    if webpage_json:
        thumbnail_json = webpage_json.get("primaryImageOfPage")
        if thumbnail_json:
            thumbnail_url.append(thumbnail_json.get("url"))
    if parsed_data.get("@type")[0] == "VideoObject":
        video_urls.append(response.url)
    elif parsed_data.get("@type")[0] == "Article":
        raw_sources = response.css('script[class="raw__source"]').getall()
        if raw_sources:
            for a_response in raw_sources:
                link_data = ((a_response.split("src="))[1]).split('"')[1::2]
                video_urls.append(link_data[0])

    return {"embed_video_link": video_urls, "thumbnail_image": thumbnail_url}


def format_dictionary(raw_dictionary):
    """Formatting dictionary with all the values converted to list

    Args:
        raw_dictionary (dict)

    Returns:
        dict: formatted dictionary
    """
    for key, value in raw_dictionary.items():
        if not isinstance(value, list):
            raw_dictionary[key] = [value]
    return raw_dictionary
