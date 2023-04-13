"""Utility Functions"""
from datetime import timedelta, datetime
import json
import os
import re
import itertools

from scrapy.loader import ItemLoader

from crwlepoint.items import (
    ArticleRawResponse,
    ArticleRawParsedJson,
)
from crwlepoint.exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)
from crwlepoint.constant import BASE_URL, SPACE_REMOVER_PATTERN

ERROR_MESSAGES = {
    "InputMissingException": "{} field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}
language_mapper = {"en": "English", "fr": "French"}



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
        True or Flase
    """
    return published_date.date() in date_range_lst


def validate_arg(param_name: str, param_value: str, custom_msg: str = None) -> None:
    """
    Validate the param.
    Args:
        param_name: Name of the parameter to be validated
        param_value: Value of the required parameter
        custom_msg: custom error message

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


def get_parsed_json_filter(blocks: list, misc: list, regex_pattern: str = "") -> dict:
    """
     Parsed json response from generated data using given response and selector
    Args:
        blocks: application/ld+json data list
        misc: misc data list
        regex_pattern: pattern to remove that type of string
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
        space_removed_block = re.sub(regex_pattern, "", block).strip()
        if "LiveBlogPosting" in json.loads(space_removed_block).get("@type", [{}]):
            parsed_json_flter_dict["main"] = json.loads(space_removed_block)
        elif ("ImageGallery" in json.loads(space_removed_block).get("@type", [{}])
              or "ImageObject" in json.loads(space_removed_block).get("@type", [{}])):
            parsed_json_flter_dict["imageObjects"].append(json.loads(space_removed_block))
        elif "VideoObject" in json.loads(space_removed_block).get("@type", [{}]):
            parsed_json_flter_dict["videoObjects"].append(json.loads(space_removed_block))
        else:
            parsed_json_flter_dict["other"].append(json.loads(space_removed_block))
    parsed_json_flter_dict["misc"].extend(json.loads(re.sub(regex_pattern, "", data).strip()) for data in misc)
    return parsed_json_flter_dict


def get_parsed_json(response: str) -> dict:
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
        SPACE_REMOVER_PATTERN
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
            f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )

    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )

    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)

    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4, ensure_ascii = False)


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
    """Recursively remove empty lists, empty dicts, or None elements from a dictionary.

    Args:
        parsed_data_dict (dict): Input dictionary.
    Returns:
        dict: Dictionary with all empty lists, and empty dictionaries removed.
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
    parsed_json_main = parsed_json.get("main")
    data_dict = get_author_and_publisher_details(parsed_json_main)
    images = get_formated_images(response, parsed_json_main)

    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= {
        "source_country": ["France"],
        "source_language": [language_mapper.get(response.css("html::attr(lang)").get())],
    }

    video_url = response.css("inline-video::attr('axis-ids')").get()
    video_link = None
    if video_url:
        video_url = (video_url.split('axisId":')[-1].split('"}')[0].replace('"', ""))
        video_link = "https://www.ctvnews.ca/video?clipId=" + video_url

    parsed_data_dict |= {"author": data_dict.get("author")}
    parsed_data_dict |= {"description": [data_dict.get("alternativeheadline")]}
    parsed_data_dict |= {"modified_at": [data_dict.get("modified_date")]}
    parsed_data_dict |= {"published_at": [data_dict.get("published_date")]}
    parsed_data_dict |= {"publisher": get_publisher_detail(response, data_dict)}
    parsed_data_dict |= {
        "title": [data_dict.get("headline")],
        "text": [re.sub(SPACE_REMOVER_PATTERN, "", " ".join(
            response.css(".twitter-tweet::text, .c-text p::text, .c-text h2::text, .c-text span::text").getall()),)],
        "section": response.css(".c-breadcrumb__item__link span::text").getall()
    }
    parsed_data_dict |= {
        "images": images,
        "video": [{"link": video_link}],
        "thumbnail_image": [data_dict.get("thumbnail_url")],
    }
    return parsed_data_dict


def get_author_and_publisher_details(block: dict) -> dict:
    """
    get author and publisher details
    Args:
        blocks: json/+ld data
    Returns:
        str : author and publisher details
    """
    if not block:
        return {}
    data_dict = {}
    data_dict["publisher_name"] = block.get("publisher", None).get("name", None)
    data_dict["publisher_type"] = block.get("publisher", None).get(
        "type", None
    )
    data_dict["logo_url"] = block.get("publisher", {}).get("logo", {}).get("url")
    data_dict["logo_width"] = block.get("publisher", {}).get("logo", {}).get("width")
    data_dict["logo_height"] = block.get("publisher", {}).get("logo", {}).get("height")
    data_dict["published_date"] = block.get("datePublished", None)
    data_dict["modified_date"] = block.get("dateModified", None)
    data_dict["headline"] = block.get("headline", None)
    data_dict["alternativeheadline"] = block.get("description", None)
    data_dict["thumbnail_url"] = block.get("thumbnailUrl", None)

    if block.get("author"):
        data_dict["author"] = data_dict.get("author", [])
        for author in block.get("author"):
            auth = {}
            auth["name"] = author.get("name")
            auth["@type"] = author.get("@type")
            auth["url"] = author.get("url")
            data_dict["author"].append(auth)
    return data_dict


def get_publisher_detail(response, data_dict: dict) -> dict:
    """generate publisher detail and return dict

    Args:
        response: reponse object scrapy
        data_dict (dict): data_dict which contains info of main

    Returns:
        dict: details of publisher to pass to json
    """
    return [{
            "@id": "www.ctvnews.ca",
            "@type": data_dict.get("publisher_type"),
            "name": data_dict.get("publisher_name"),
            "logo": {
                "type": "ImageObject",
                "url": BASE_URL + data_dict.get("logo_url"),
                "width":{
                     "@type":"Distance",
                     "name":f"{data_dict.get('logo_width')} px"
                  },
                "height":{
                     "@type":"Distance",
                     "name":f"{data_dict.get('logo_height')} px"
                  }
            }}]


def get_image_url(response) -> str:
    """return image url from response

    Args:
        response : response object of scrapy

    Returns:
        str: return link of image
    """
    images = []
    imageurls = response.css("div.c-heroMedia div.c-image img::attr(src)").getall()
    for img in imageurls:
        images.append(get_full_url(img))
    return images


def get_formated_images(response, block) -> str:
    """return formated images response using block and response
    Args:
        response : response object of scrapy
    Returns:
        str: return link of image
    """
    formated_images = []
    images = get_image_url(response)
    captions = response.css("span.c-image__title::text").getall()
    for link, caption in itertools.zip_longest(images, captions):
        if not link_in_images(formated_images, link):
            formated_images.append({
                "link": link,
                "caption": caption,
            })
    for link, caption in itertools.zip_longest(
        response.css(
            "figure.o-element__main picture.o-element__image source[data-breakpoint='Large']::attr(data-src-template), \
            figure.o-element__main picture.o-element__image img::attr(src)")
        .getall(),
        response.css(
            "figure.o-element__main figcaption div.o-element__text[data-qa='Element.Caption.text']::text")
        .getall()
    ):
        if not link_in_images(formated_images, link):
            formated_images.append({
                "link": link,
                "caption": caption,
            })
    if formated_images:
        return formated_images
    captions = []
    caption_blocks = response.css("div.aem-Grid--default--7 related-images::attr(content)").get()
    # for captions_block in json.loads(caption_blocks):
    #     captions.append(captions_block.get("description"))
    if block:
        image_url_from_block = block.get("image", {}).get("url")
        if image_url_from_block:
            formated_images.append({
                "link": image_url_from_block,
                "caption": captions[0] if captions else None
            })
            return formated_images
    caption = response.css('.o-element__text::text').get()
    image_link = response.css('.c-progressive-opener-image__original-image img::attr(src)').get()
    image_link2 = response.css("picture.o-element__image source::attr(data-src-template)").get()
    if caption and (image_link or image_link2):
        formated_images.append({
            "link": image_link or image_link2,
            "caption": caption.strip() if caption else None
        })
    return formated_images


def link_in_images(formated_images: list, link: str) -> bool:
    """return true if link in list of dictionary of image

    Args:
        formated_images (list): list of dict of images
        link (str): link

    Returns:
        bool: true if link present
    """
    if not link:
        return True
    for formated_image in formated_images:
        if link == formated_image.get("link"):
            return True
    return False


def get_full_url(link: str) -> str:
    """add base url to short url
    Args:
        link (str): link of image or any type
    Returns:
        str: Full url including base url
    """
    if BASE_URL not in link and len(link) > 20:
        return BASE_URL + link
    return link


