import json
import os
from datetime import datetime
from scrapy.loader import ItemLoader
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crwmbnnewsonline.constant import SITEMAP_URL
from crwmbnnewsonline.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from crwmbnnewsonline.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
    SitemapArticleScrappingException
)
from crwmbnnewsonline.constant import LOGGER


def check_cmd_args(self, start_date: str, end_date: str) -> None:  # noqa: C901
    """
    Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.
    Args:
        self (TimesNow): The TimesNow spider instance.
        start_date (str): The start date for the sitemap spider in the format YYYY-MM-DD.
        end_date (str): The end date for the sitemap spider in the format YYYY-MM-DD.
    Raises:
        ValueError: If the type is not "articles" or "sitemap".
        ValueError: If the type is "sitemap" and either start_date or end_date is missing.
        ValueError: If the type is "sitemap" and the time range is more than 30 days.
        ValueError: If the type is "articles" and the URL is missing.
    Returns:
        None.
    Note:
        This function assumes that the class instance variable `start_urls` is already initialized as an empty list.
    """

    def add_start_url(url):
        self.start_urls.append(url)

    def set_date_range(start_date, end_date):
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')

    def validate_date_range():
        if self.start_date > self.end_date:
            raise InvalidDateException("start_date must be less then end_date")
        if (self.end_date - self.start_date).days > 30:
            raise InvalidDateException("Enter start_date and end_date for maximum 30 days.")

    def validate_type():
        if self.type not in ["article", "sitemap"]:
            raise InvalidArgumentException("type should be articles or sitemap")

    def handle_sitemap_type():
        if self.end_date is not None and self.start_date is not None:
            set_date_range(start_date, end_date)
            validate_date_range()
            add_start_url(SITEMAP_URL)

        elif self.start_date is None and self.end_date is None:
            today_time = datetime.today().strftime("%Y-%m-%d")
            self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
            add_start_url(SITEMAP_URL)

        elif self.end_date is not None or self.start_date is not None:
            raise InvalidArgumentException("to use type sitemap give only type sitemap or with start date and end date")

    def handle_article_type():
        if self.url is not None:
            add_start_url(self.url)
        else:
            raise InputMissingException("type articles must be used with url")

    validate_type()

    if self.type == "sitemap":
        handle_sitemap_type()

    elif self.type == "article":
        handle_article_type()


def get_raw_response(response: str, selector_and_key: dict) -> dict:
    """
    Raw response data generated from given response and selector
    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector
    Returns:
        Dictionary with generated raw response
    """
    article_raw_response_loader = ItemLoader(
        item=ArticleRawResponse(), response=response
    )
    for key, value in selector_and_key.items():
        article_raw_response_loader.add_value(key, value)
    return dict(article_raw_response_loader.load_item())


def get_parsed_json(response: str, selector_and_key: dict) -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector
    Returns:
        Dictionary with Parsed json response from generated data
    """

    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in selector_and_key.items():

        if key == "main":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if "NewsArticle" in json.loads(data).get('@type')]
            )
        elif key == "ImageGallery":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "ImageGallery"]
            )

        elif key == "VideoObject":
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') == "VideoObject"]
            )
        else:
            article_raw_parsed_json_loader.add_value(
                key, [json.loads(data) for data in value.getall() if json.loads(data).get('@type') not in
                      selector_and_key.keys() and json.loads(data).get('@type') != "NewsArticle"]
            )

    return dict(article_raw_parsed_json_loader.load_item())


def get_parsed_data_dict() -> dict:
    """
    Return base data dictionary
    Args:
    None
    Returns:
        dict: Return base data dictionary
    """
    return {
        "country": None,
        "language": None,
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
        "video": None,
    }


def get_parsed_data(response: str, parsed_json_dict: dict) -> dict:
    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )
    for key, value in parsed_json_dict.items():
        article_raw_parsed_json_loader.add_value(
            key, [json.loads(data) for data in value.getall()]
        )
    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict["description"] = [response.css('meta[name="dc.description"]::attr(content)').get()]
    published_at = response.css('.txt_box span.time::text').getall()
    i = 0
    if len(published_at) == 3:
        i = 1
    parsed_data_dict["published_at"] = [published_at[i].split(' ')[2] + 'T' + published_at[i].split(' ')[3]]
    if len(published_at) > 1:
        parsed_data_dict["modified_at"] = [published_at[i + 1].split(' ')[3] + 'T' + published_at[i + 1].split(' ')[4]]
    author = {}
    if response.css('#container a::text')[0].get():
        author['@type'] = 'Person'
        author['name'] = response.css('#container a::text')[0].get()
        author['url'] = response.css('#container a::attr(href)')[0].get()
        parsed_data_dict['author'] = [author]
    parsed_data_dict['author'] = [author]
    texts = []
    for data in response.css('#newsViewArea::text'):
        texts.append(data.get().strip())
    parsed_data_dict["text"] = [" ".join(data for data in texts if data)]
    parsed_data_dict['thumbnail_image'] = [response.css('h1 a:nth-child(1) img::attr(src)').get()]
    parsed_data_dict['title'] = [response.css('#container h1::text').get()]
    parsed_data_dict['section'] = [response.css('.section::text').get().split('>')[1]]
    # parsed_data_dict['embed_video_link'] = get_embed_video_link(response)
    parsed_data_dict["source_country"] = ["South Korea"]
    parsed_data_dict["source_language"] = ["Korean"]
    parsed_data_dict['tags'] = response.css('.gnb_depth_in li a::text').getall()
    parsed_data_dict['images'] = get_images(response)
    return remove_empty_elements(parsed_data_dict)


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param parsed_data_dict: Input dictionary.
    :type parsed_data_dict: dict
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


def get_images(response, parsed_json=False) -> list:
    """
    Extracts all the images present in the web page.
    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(response.url)

    try:
        scroll = driver.find_elements(By.XPATH, "//p")
        last_p_tag = scroll[-1]
        driver.execute_script(
            "window.scrollTo("
            + str(last_p_tag.location["x"])
            + ", "
            + str(last_p_tag.location["y"])
            + ")"
        )
        import time
        time.sleep(1)
        data = []
        images = driver.find_elements(By.CSS_SELECTOR, '#newsViewArea .b-loaded')
        if images:
            for image in images:
                temp_dict = {}
                link = image.get_attribute("src")
                caption = image.get_attribute("alt")
                if link:
                    temp_dict["link"] = link
                    if caption:
                        temp_dict["caption"] = caption
                data.append(temp_dict)
            return data
    except Exception as e:
        LOGGER.error(f"{str(e)}")
        raise SitemapArticleScrappingException(f"Error occured while scrapping sitemap:-{str(e)}")
    driver.close()
    return data
