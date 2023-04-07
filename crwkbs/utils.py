""" General functions """
from datetime import timedelta, datetime
import json
import os

from scrapy.loader import ItemLoader

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from crwkbs.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)

from crwkbs.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)

ERROR_MESSAGES = {
    "InputMissingException": "'{}' field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}
language_mapper = {"ko": "KOREA", "en": "ENGLISH"}

# Regex patterns
SPACE_REMOVER_PATTERN = r"[\n|\r|\t]+"


def sitemap_validations(
    scrape_start_date: datetime, scrape_end_date: datetime, article_url: str
) -> datetime:
    """
    Validate the sitemap arguments
    Args:
        scrape_start_date (datetime): scrapping start date
        scrape_end_date (datetime): scrapping end date
        article_url (str): article url
    Returns:
        date: return current date if user not passed any date parameter
    """
    if scrape_start_date and scrape_end_date:
        validate_arg(
            InvalidDateException,
            scrape_start_date <= datetime.now().date()
            and scrape_end_date <= datetime.now().date(),
        )
        validate_arg(InvalidDateException, not scrape_start_date > scrape_end_date)
        validate_arg(
            InvalidDateException,
            int((scrape_end_date - scrape_start_date).days) <= 30,
        )
    else:
        validate_arg(
            InputMissingException,
            not (scrape_start_date or scrape_end_date),
            "start_date and end_date",
        )
        scrape_start_date = scrape_end_date = datetime.now().date()

    validate_arg(
        InvalidArgumentException, not article_url, "url is not required for sitemap."
    )

    return scrape_start_date, scrape_end_date


def article_validations(
    article_url: str, scrape_start_date: datetime, scrape_end_date: datetime
) -> None:
    """
    Validate the article arguments

    Args:
        article_url (str): article url
        scrape_start_date (datetime): scrapping start date
        scrape_end_date (datetime): scrapping end date
    Returns:
        None
    """

    validate_arg(InputMissingException, article_url, "url")
    validate_arg(
        InvalidArgumentException,
        not (scrape_start_date or scrape_end_date),
        "start_date and end_date argument is not required for article.",
    )


def date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Return range of all date between given date
    if not end_date then take start_date as end date

    Args:
        start_date (datetime): scrapping start date
        end_date (datetime): scrapping end date
    Returns:
        Value of parameter
    """
    for date_count in range(int((end_date - start_date).days) + 1):
        yield (start_date + timedelta(date_count)).strftime("%Y%m%d")


def date_in_date_range(published_date, date_range_lst):
    """
    return true if date is in given start date and end date range
    """
    return published_date.date() in date_range_lst


def validate_arg(param_name, param_value, custom_msg="") -> None:
    """
    Validate the param.

    Args:
        param_name: Name of the parameter to be validated
        param_value: Value of the required parameter

    Raises:
        ValueError if not provided
    Returns:
          Value of parameter
    """
    if not param_value:
        raise param_name(f"{ERROR_MESSAGES[param_name.__name__]} {custom_msg}")


def based_on_scrape_type(
    scrape_type: str, scrape_start_date: datetime, scrape_end_date: datetime, url: str
) -> datetime:
    """
    check scrape type and based on the type pass it to the validated function,
    after validation return required values.

     Args:
         scrape_type: Name of the scrape type
         scrape_start_date (datetime): scrapping start date
         scrape_end_date (datetime): scrapping end date
         url: url to be used

     Returns:
         datetime: if scrape_type is sitemap
         list: if scrape_type is sitemap
    """
    if scrape_type == "article":
        article_validations(url, scrape_start_date, scrape_end_date)
        return None
    if scrape_type == "sitemap":
        scrape_start_date, scrape_end_date = sitemap_validations(
            scrape_start_date, scrape_end_date, url
        )
        date_range_lst = []
        date_range_lst.extend(iter(date_range(scrape_start_date, scrape_end_date)))
        return date_range_lst

    return validate_arg("MISSING_REQUIRED_FIELD", None, "type")


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


def get_parsed_json_filter(blocks: list, misc: list) -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        blocks: application/ld+json data list
        misc: misc data list
    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_json_flter_dict = {
        "main": None,
        "imageObjects": [],
        "videoObjects": [],
        "other": [],
        "misc": [],
    }
    for block in blocks:
        if "NewsArticle" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(block)
        elif "ImageGallery" in json.loads(block).get(
            "@type", [{}]
        ) or "ImageObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["imageObjects"].append(json.loads(block))
        elif "VideoObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["videoObjects"].append(json.loads(block))
        else:
            parsed_json_flter_dict["other"].append(json.loads(block))
    parsed_json_flter_dict["misc"] = [json.loads(data) for data in misc]
    return parsed_json_flter_dict


def get_parsed_json(response) -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        response: provided response
    Returns:
        Dictionary with Parsed json response from generated data
    """
    article_raw_parsed_json_loader = ItemLoader(
        item=ArticleRawParsedJson(), response=response
    )

    for key, value in get_parsed_json_filter(
        response.css('script[type="application/ld+json"]::text').getall(),
        response.css('script[type="application/json"]::text').getall(),
    ).items():
        article_raw_parsed_json_loader.add_value(key, value)

    return dict(article_raw_parsed_json_loader.load_item())


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
        filename = (
            f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )

    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)

    with open(f"{folder_structure}/{filename}", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4, ensure_ascii=False)


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
        "video": None,
    }


def remove_empty_elements(parsed_data_dict: dict) -> dict:
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param parsed_data_dict: Input dictionary.
    :type parsed_data_dict: dict
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


def get_parsed_data(self, response: str, parsed_json_main: list) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_data_dict = get_parsed_data_dict()

    parsed_data_dict |= {
        "source_country": ["KOREA"],
        "source_language": [
            language_mapper.get(response.css("html::attr(lang)").get(), None)
        ],
    }
    parsed_data_dict |= get_author_details(parsed_json_main)
    parsed_data_dict |= get_descriptions_date_details(parsed_json_main)
    parsed_data_dict |= get_publisher_details(parsed_json_main)
    parsed_data_dict |= get_text_title_section_details(parsed_json_main, response)
    parsed_data_dict |= get_thumbnail_image(parsed_json_main, response)
    parsed_data_dict |= get_videos(self, response)
    return remove_empty_elements(parsed_data_dict)


def get_author_details(parsed_data: list) -> dict:
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: author related details
    """
    author_details = []
    author_data = (
        parsed_data.get("author")
        if isinstance(parsed_data.get("author"), list)
        else [parsed_data.get("author")]
    )

    author_details.extend(
        {
            "@type": author.get("@type"),
            "name": author.get("name"),
            "url": author.get("url", None),
        }
        for author in author_data
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
    article_data = {
        "description": None,
        "modified_at": None,
        "published_at": None,
        "time_scraped": None,
    }
    if "NewsArticle" in parsed_data.get("@type"):
        article_data |= {
            "description": [parsed_data.get("description")],
            "modified_at": [parsed_data.get("dateModified")],
            "published_at": [parsed_data.get("datePublished")],
            "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
        }
    return article_data


def get_publisher_details(parsed_data: list) -> dict:
    """
    Returns publisher details like name, type, id
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: publisher details like name, type, id related details
    """
    publisher_details = []
    if parsed_data.get("publisher"):
        publisher_details.extend(
            {
                "@id": publisher.get("@id"),
                "@type": publisher.get("@type"),
                "name": publisher.get("name"),
                "logo": {
                    "url": parsed_data.get("publisher").get("logo").get("url"),
                    "width": str(
                        parsed_data.get("publisher").get("logo").get("width", None)
                    )
                    + " px",
                },
            }
            for publisher in [parsed_data.get("publisher")]
        )
    return {"publisher": publisher_details}


def get_text_title_section_details(parsed_data: list, response: str) -> dict:
    """
    Returns text, title, section details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: text, title, section details
    """
    if "NewsArticle" in parsed_data.get("@type"):
        return {
            "title": [parsed_data.get("headline")],
            "text": [
                "".join(
                    x.strip() for x in response.css("div.detail-body::text").extract()
                )
            ],
            "section": response.css("span.source a::text").getall(),
            "tags": response.css("meta[name='keywords']::attr(content)").getall(),
        }

    return {
        "title": response.css(".landing-caption h5::text").getall(),
        "text": ["".join(response.css("div.detail-body::text").extract())],
        "section": response.css("span.source a::text").getall(),
        "tags": response.css("meta[name='keywords']::attr(content)").getall(),
    }


def get_thumbnail_image(parsed_data: list, response: str) -> dict:
    """
    Returns thumbnail images, images.
    Args
        parsed_data: response of application/ld+json data
    Returns:
        dict: thumbnail images, images.
    """
    image = None
    if not response.css("#btnMainPlay").get():
        image = parsed_data.get("image", {}).get("url")
    return {
        "thumbnail": [parsed_data.get("image", {}).get("url")],
        "images": [
            {"link": image}
        ]
    }


def get_videos(self, response: str) -> list:
    """
    Returns video url.
    Args
        response: video url
    Returns:
        str: video
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(response.url)
    try:
        driver.find_element(By.XPATH, '//*[@id="btnMainPlay"]').click()
        videos = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="JW_PLAYER"]/div[2]/video')
            )
        )
        return {"video": [
            {"link": videos.get_attribute("src")}
        ]}
    except Exception as exception:
        self.error_msg_dict["error_msg"] = (
            "Error occurred while taking type, url, start_date and end_date args. "
            + str(exception)
        )
        return {"videos": None}
    driver.quit()
