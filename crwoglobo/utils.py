"""Utility Functions"""
from datetime import timedelta, datetime
import json
import re
import itertools

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

from scrapy.loader import ItemLoader

from crwoglobo.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from crwoglobo.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)
from crwoglobo.constant import BASE_URL, SPACE_REMOVER_PATTERN

ERROR_MESSAGES = {
    "InputMissingException": "{} field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}

language_mapper = {"en": "English", "pt-br": "Portuguese (Brazil)"}


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
        validate_arg(InvalidDateException, not scrape_start_date > scrape_end_date)
        validate_arg(
            InvalidDateException,
            int((scrape_end_date - scrape_start_date).days) <= 30,
        )
    else:
        validate_arg(
            InputMissingException,
            not (scrape_start_date or scrape_end_date),
            "since and until",
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
        "since and until argument is not required for article.",
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
    for date in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(date)


def date_in_date_range(published_date: datetime, date_range_lst: list) -> bool:
    """
    return true if date is in given start date and end date range

    Args:
        published_date (datetime): published date for checking exsist or not in date range list
        date_range_lst (list): date range list
    Returns:
        Value of parameter
    """
    return published_date.date() in date_range_lst


def validate_arg(param_name, param_value, custom_msg=None) -> None:
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
        raise param_name(ERROR_MESSAGES[param_name.__name__].format(custom_msg))


def validate(
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
        elif ("ImageGallery" in json.loads(block).get("@type", [{}])
              or "ImageObject" in json.loads(block).get("@type", [{}])):
            parsed_json_flter_dict["imageObjects"].append(json.loads(block))
        elif "VideoObject" in json.loads(block).get("@type", [{}]):
            parsed_json_flter_dict["videoObjects"].append(json.loads(block))
        else:
            parsed_json_flter_dict["other"].append(json.loads(block))
    parsed_json_flter_dict["misc"].append(misc)
    return parsed_json_flter_dict


def get_parsed_json(response) -> dict:
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

    for key, value in get_parsed_json_filter(
        response.css('script[type="application/ld+json"]::text').getall(),
        response.css('script[type="application/json"]::text').getall(),
    ).items():
        article_raw_parsed_json_loader.add_value(key, value)

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
            if not empty(value) or key == "parsed_json"
        }
    return data_dict


def get_parsed_data(response: str, parsed_json: dict) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """
    parsed_json_images = parsed_json.get("imageObjects")
    parsed_json_main = parsed_json.get("main")
    parsed_json_misc = parsed_json.get("misc")
    response_detail = get_all_detail_from_response(response)

    data_dict = get_all_details_of_block(parsed_json_main, parsed_json_misc)

    images = response_detail.get("images")
    if not images:
        images = get_formated_images(response, parsed_json_main, parsed_json_images)

    if data_dict.get("description"):
        description = [data_dict.get("description")]
    elif response_detail.get("alternativeHeadline"):
        description = [response_detail.get("alternativeHeadline")]
    else:
        description = response.xpath("//meta[@name='description']/@content").extract()
    

    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= {
        "source_country": ["brazil"],
        "source_language": [language_mapper.get(
            response.css("html::attr(lang)").get("").lower(),
            response.css("html::attr(lang)").get()
        )],
    }
    parsed_data_dict |= {"author": response_detail.get("authors") or data_dict.get("author")}
    parsed_data_dict |= {
        "description": description
    }
    parsed_data_dict |= {"modified_at": [data_dict.get("modified_at") or response_detail.get("date_published")]}
    parsed_data_dict |= {"published_at": [data_dict.get("published_at") or response_detail.get("date_modified")]}
    parsed_data_dict |= {"publisher": get_publisher_detail(data_dict)}
    parsed_data_dict |= {
        "title": [response_detail.get("title")] if response_detail.get("title")
        else response.css("title::text").getall(),
        "text": [response_detail.get("text")],
        "thumbnail_image": [data_dict.get("thumbnail_image")],
        "section": [data_dict.get("section")] or [response_detail.get("section")],
        "tags": data_dict.get("tags")
    }
    parsed_data_dict |= {
        "images": images,
    }
    return remove_empty_elements(parsed_data_dict)


def get_all_detail_from_response(response) -> dict:
    """get all detail from response using scrapping

    Args:
        response (response): response of scrapy parse function

    Returns:
        dict: detail of all details in dict
    """
    images = []
    captions = response.css("span.name::text, span.name font::text").getall()
    if not captions:
        captions = (" ".join(response.css("figure figcaption::text").getall())).split("1 de 1 \r")
    for image_link, caption in itertools.zip_longest(
        response.css("figure img::attr(src)").getall(), captions
    ):
        if image_link:
            images.append({
                "link": image_link,
                "caption": caption
            })
    text = " ".join(text.strip() for text in response.css("article p::text,article p a::text,article li::text,\
                                 article li a::text,article h3::text, article strong::text, article h2::text,\
                                 article font::text,article::text").getall())
    space_removed_text = re.sub(SPACE_REMOVER_PATTERN, "", text).strip()
    authors = response.css("p.content-publication-data__from::attr(title)").getall()
    for author_name in [author.replace("Por","").strip() for author in response.css("p.content-publication-data__from::attr(title)").getall()]:
        if author_name not in authors:
            authors.append(author_name)
    author_dict_list = []
    for author in authors:
        author_dict_list.append({
            "name": author
        })

    return {
        "title": response.css("h1.content-head__title::text").get() or response.css("title::text").get(),
        "alternativeHeadline": response.css("h2.content-head__subtitle::text").get(),
        "authors": author_dict_list,
        "date_published": response.css("time[itemprop='datePublished']::attr(datetime)").getall(),
        "date_modified": response.css("time[itemprop='dateModified']::attr(datetime)").getall(),
        "images": images,
        "text": space_removed_text
    }



def get_all_details_of_misc_block(misc_block) -> dict:
    """get realted details from misc block and return related dict

    Args:
        misc_block (dict): misc block of application json

    Returns:
        dict: data from misc block
    """

    data_dict = {
        "description": misc_block.get("description", "").strip(),
        "modified_at": misc_block.get("modified_time"),
        "published_at": misc_block.get("published_time"),
        "publisher_name": misc_block.get("publisher", {}),
        "title": misc_block.get("headline", {}),
        "thumbnail_image": misc_block.get("thumbnailUrl"),
        "category": misc_block.get("category"),
        "tags": misc_block.get("tag"),
        "section": misc_block.get("section"),
        "image": misc_block.get("image")
    }
    data_dict["author"] = []
    if misc_block.get("authors"):
        author_names = misc_block.get("authors", [])
        if not isinstance(author_names, list) and isinstance(author_names, str):
            author_names_list = [author_names]
        else:
            author_names_list = author_names
        for author_name in author_names_list:
            data_dict["author"].append({
                "name": author_name
            })
    return data_dict


def get_all_details_of_block(block: dict, parsed_json_misc: dict) -> dict:
    """
    get all details from main block
    Args:
        block: json/+ld data
        misc_block: json block
    Returns:
        str : author and publisher details
    """
    misc_block_string = re.sub(SPACE_REMOVER_PATTERN, "", parsed_json_misc[0][0]).strip()
    if not block:
        return get_all_details_of_misc_block(json.loads(misc_block_string))
    data_dict = {
        "description": block.get("description", "").strip(),
        "modified_at": block.get("dateModified"),
        "published_at": block.get("datePublished"),
        "publisher_id": block.get("publisher", {}).get("url"),
        "publisher_type": block.get("publisher", {}).get("@type"),
        "publisher_name": block.get("publisher", {}).get("name"),
        "logo_type": block.get("publisher", {}).get("logo", {}).get("@type"),
        "logo_url": block.get("publisher", {}).get("logo", {}).get("url"),
        "logo_width": block.get("publisher", {}).get("logo", {}).get("width"),
        "logo_height": block.get("publisher", {}).get("logo", {}).get("height"),
        "title": block.get("headline", {}),
        "thumbnail_image": block.get("thumbnailUrl"),
        "headline": block.get("headline"),
        "tags": block.get("keywords"),
        "sections": block.get("articleSection")
    }
    data_dict["author"] = []
    if block.get("author"):
        author_names = block.get("author").get("name", [])
        if not isinstance(author_names, list) and isinstance(author_names, str):
            author_names_list = [author_names]
        else:
            author_names_list = author_names
        for author_name in author_names_list:
            data_dict["author"].append({
                "@type": block.get("author").get("@type"),
                "name": author_name
            })
    return data_dict


def get_formated_images(response, block, image_block, image_url_data: dict = dict()) -> list:
    """return formated images response using block and response

    Args:
        response : response object of scrapy
        block : main block of ld+json
        image_block : imageobjects block of ld+json
        image_url_data : data of image url

    Returns:
        str: return link of image
    """
    image_links = []
    if block:
        if block.get("image", {}).get("url"):
            image_links.append(block.get("image", {}).get("url"))
    for image in image_block or []:
        if image and (image.get("url") not in image_links):
            image_links.append(image.get("url"))
    if image_url_data:
        images_urls_from_response = image_url_data.get("image_urls")
    else:
        images_urls_from_response = response.css('picture.image-gallery-img img::attr(src)').getall()
    for image_link in images_urls_from_response:
        if image_link and (image_link not in image_links):
            image_links.append(image_link)

    captions = response.css('span.article-detail_caption::text').getall()
    formated_images = []
    for link, caption in itertools.zip_longest(image_links, captions):
        if get_full_url(link):
            formated_images.append({
                "link": get_full_url(link),
                "caption": caption,
            })
    return formated_images


def get_full_url(link: str) -> str:
    """add base url to short url

    Args:
        link (str): link of image or any type

    Returns:
        str: Full url including base url
    """
    if link and "hket.com" not in link and len(link) > 20:
        return BASE_URL + link[1:]
    return link


def get_publisher_detail(data_dict: dict) -> list:
    """generate publisher detail and return dict

    Args:
        data_dict (dict): data_dict which contains info of main

    Returns:
        dict: details of publisher to pass to json
    """
    return [{
            "@id": data_dict.get("publisher_id", ""),
            "@type": data_dict.get("publisher_type"),
            "name": data_dict.get("publisher_name"),
            "logo": {
                "type": data_dict.get("logo_type", "ImageObject"),
                "url": data_dict.get("logo_url"),
                "width": {
                    "@type": "Distance",
                    "name": f"{data_dict.get('logo_width')} px"
                } if data_dict.get("logo_width") else None,
                "height": {
                    "@type": "Distance",
                    "name": f"{data_dict.get('logo_height')} px"
                } if data_dict.get("logo_width") else None
            }}]
