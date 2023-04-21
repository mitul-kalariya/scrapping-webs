# Utility/helper functions
# utils.py
import json
import logging
import os
from datetime import datetime

from crwrecordnews import exceptions
from crwrecordnews.constant import LOGGER, TODAYS_DATE


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(since, until):
    """validate date range given by user
    Args:
        start_date (datetime): start_date
        end_date (datetime): end date
    Raises:
        exceptions.InvalidDateException: end_date must be specified if start_date is provided
        exceptions.InvalidDateException: start_date must be specified if end_date is provided
        exceptions.InvalidDateException: start_date should not be later than end_date
        exceptions.InvalidDateException: start_date should not be greater than today_date
        exceptions.InvalidDateException: end_date should not be greater than today_date
    """
    since = datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
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
    except exceptions.InvalidDateException as expception:
        LOGGER.info(f"Error occured while checking date range: {expception}")
        raise exceptions.InvalidDateException(
            f"Error occured while checking date range: {expception}"
        )


def get_raw_response(response):
    """generate dictrionary of raw html data
    Args:
        response (object): page_data
    Returns:
        raw_response (dict): targeted data
    """
    try:
        raw_resopnse = {
            "content_type": "text/html; charset=utf-8",
            "content": response.css("html").get(),
        }
        return raw_resopnse
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting raw response: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting raw response: {exception}"
        )


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
            'script[type="application/ld+json"]::text'
        ).getall()[0]
        ld_json_list = json.loads(ld_json_data)

        for data in ld_json_list:
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
        parsed_json["Other"] = other_data
        misc = get_misc(response)
        if misc:
            parsed_json["misc"] = misc

        return remove_empty_elements(parsed_json)
    except Exception as exception:
        LOGGER.info(f"Error while parsing json from application/ld+json: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsing json from application/ld+json: {exception}"
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
        data = []
        misc = response.css('script[type="application/ld+json"]::text').getall()
        for block in misc:
            data.append(json.loads(block))
        return data
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


def get_parsed_data(response):
    """
    Extracts data from a news article webpage and returns it in a dictionary format.
    Parameters:
    response (scrapy.http.Response): A scrapy response object of the news article webpage.
    Returns:
    dict: A dictionary containing the extracted data from the webpage, including:
        - 'breadcrumbs': (list) The list of breadcrumb links to the article, if available.
        - 'published_on': (str) The date and time the article was published.
        - 'last_updated': (str) The date and time the article was last updated, if available.
        - 'headline': (str) The headline of the article.
        - 'description': (str) The description of the article, if available.
        - 'publisher': (str) The name of the publisher of the article.
        - 'authors': (list) The list of authors of the article, if available.
        - 'video': (str) The video URL of the article, if available.
        - 'thumbnail_image': (str) The URL of the thumbnail image of the article, if available.
        - 'subheadings': (list) The list of subheadings in the article, if available.
        - 'text': (list) The list of text paragraphs in the article.
        - 'images': (list) The list of image URLs in the article, if available.
    """
    try:
        main_dict = {}

        ld_json_data = response.css(
            'script[type="application/ld+json"]::text'
        ).getall()[0]
        ld_json_list = json.loads(ld_json_data)
        json_new_article = new_articles_info(ld_json_list)
        
        # Author
        authors = get_author(json_new_article)
        main_dict["author"] = authors

        # Last Updated Date
        last_updated = get_lastupdated(json_new_article)
        main_dict["modified_at"] = [last_updated]

        # Published Date
        published_on = get_published_at(json_new_article)
        main_dict["published_at"] = [published_on]

        # Description
        description_data = response.css("meta[property='og:description']")
        description = description_data.attrib.get("content")
        main_dict["description"] = [description]

        # Publisher
        publisher = get_publisher(json_new_article)
        main_dict["publisher"] = publisher

        # Article Text
        article_text = get_text(response)
        main_dict['text'] = article_text

        # Thumbnail
        thumbnail = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail

        # Title
        headline = json_new_article.get('headline')
        main_dict["title"] = [headline]

        # Article Image
        article_images = get_images(response)
        main_dict["images"] = article_images

        # Language
        mapper = {"pt": "Portuguese"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang.split("-")[0])]

        # Tags
        main_dict["tags"] = get_tags(response)

        # Section/Category
        main_dict["section"] = get_section(response)

        return remove_empty_elements(main_dict)
    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_lastupdated(ld_json_data) -> str:
    """
    This function extracts the last updated date and time of an article from a given Scrapy response object.
    It returns a string representation of the date and time in ISO 8601 format.
    If the information is not available in the response, it returns None.
    Args:
        response: A Scrapy response object representing the web page from which to extract the information.
    """
    try:
        info = ld_json_data.get('dateModified')
        if info:
            return info
    except Exception as exception:
        LOGGER.info(f"Error while extracting last updated date: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting last updated date: {exception}"
        )


def get_published_at(ld_json_data) -> str:
    """get data of when article was published
    Args:
        response (object):page data
    Returns:
        str: datetime of published date
    """
    try:
        info = ld_json_data.get('datePublished')
        if info:
            return info
    except Exception as exception:
        LOGGER.info(f"Error while extracting published date: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting published date: {exception}"
        )


def get_author(ld_json_data) -> list:
    """
    The extract_author function extracts information about the author(s)
    of an article from the given response object and returns it in the form of a list of dictionaries.
    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        A list of dictionaries, where each dictionary contains information about one author.
    """
    try:
        author = ld_json_data.get('author')
        author_info = {
            "@type" : author.get("@type"),
            "name" : author.get('name'),
            "url" : author.get("url"),
        }
        return author_info
    except Exception as exception:
        LOGGER.info(f"Error while extracting author information: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting author information: {exception}"
        )


def new_articles_info(ld_json_list):
    for json_data in ld_json_list:
        if json_data.get('@type') == 'NewsArticle':
            json_new_article = json_data
    return json_new_article


def get_text(response) -> list:
    data = []
    article_text = response.css(
            ".toolkit-media-content::text"
    ).getall()        
    data.append(" ".join(article_text).replace("\n", "").replace(" ", ""))
    return data

def get_thumbnail_image(response) -> list:
    """
    Extracts information about the thumbnail image(s) associated with a webpage,
    including its link, width, and height, and returns the information as a list of dictionaries.
    Returns:
        A list of dictionaries, with each dictionary containing information about an image.
            If no images are found, an empty list is returned.
    """
    data = {}
    try:
        data = []
        thumbnails = response.css('.toolkit-media-content .toolkit-image-container__edges img::attr(src)').get()
        if thumbnails:
            data.append(thumbnails)
            return data 
    except Exception as exception:
        LOGGER.info(f"Error while extracting thumbnail image: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting thumbnail image: {exception}"
        )
    


def get_publisher(ld_json_data) -> list:
    """
    Extracts publisher information from the given response object and returns it as a dictionary.
    Returns:
    - A dictionary containing information about the publisher. The dictionary has the following keys:
        - "@id": The unique identifier for the publisher.
        - "@type": The type of publisher (in this case, always "NewsMediaOrganization").
        - "name": The name of the publisher.
    """
    try:
        publisher_data = ld_json_data.get("publisher")
        a_dict = {
            "@id": "noticias.r7.com",
            "@type": publisher_data.get("@type"),
            "name": publisher_data.get("name"),
            "logo": {
                "@type": publisher_data.get("logo").get("@type"),
                "url": publisher_data.get("logo").get("url"),
                "width": {
                    "@type": "Distance",
                    "name": str(publisher_data.get("logo").get("width")) + " px"
                },
                "height": {
                    "@type": "Distance",
                    "name": str(publisher_data.get("logo").get("height")) + " px"
                },
            },
        }
        return [a_dict]
    except Exception as exception:
        LOGGER.info(f"Error while extracting publisher information: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting publisher information: {exception}"
        )


def get_images(response) -> list:
    """
    Extracts all the images present in the web page.
    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    try:
        data = []
        images_data = {}
        article_images = response.css('.toolkit-media-content .toolkit-image-container__edges img::attr(src)').getall()
        article_image_caption = response.css('.toolkit-media-content .toolkit-image-container__edges img::attr(alt)').getall()

        for image, caption in zip(article_images, article_image_caption):
            if caption:
                images_data = {
                    'link' : image,
                    'caption' : caption
                }
            else:
                images_data = {
                    'link' : image,
                }
            data.append(images_data)
        return data
    except Exception as exception:
        LOGGER.info(f"Error while extracting article image: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting article image: {exception}"
        )


def get_tags(response) -> list:
    """Extract all the tags available for the article

    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        list: List of tags
    """
    try:
        meta_tags = response.css(
            "meta[name='keywords']"
        )
        
        tags_data = meta_tags.attrib.get("content")
        if tags_data:
            tags = tags_data.split(",")
        return tags
    except Exception as exception:
        LOGGER.info(f"Error while extracting article tags: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting article tags: {exception}"
        )

def get_section(response) -> list:
    """Extract all the sections/sub sections available for the article

    Args:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        list: List of sections
    """
    try:
        meta_tags = response.css(
            "meta[property='article:section']"
        )
        
        tags_data = meta_tags.attrib.get("content")
        if tags_data:
            tags = tags_data.split(",")
        return tags
    except Exception as exception:
        LOGGER.info(f"Error while extracting article section: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting article section: {exception}"
        )


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param d: Input dictionary.
    :type d: dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
    :rtype: dict
    """
    try:
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
    except exceptions.ArticleScrappingException as exception:
        LOGGER.error(f"{str(exception)}")
        print(f"Error while removing empty elements: {str(exception)}")


def find_key(obj, key):
    """
    Recursively finds all occurrences of a key in a nested dictionary or a list of dictionaries.
    """
    results = []
    if isinstance(obj, dict):
        if key in obj:
            img_dict = dict(([key, obj.get(key)],))
            img_dict.update({
                "caption": obj.get("caption")
            })
            results.append(img_dict)
        for k, v in obj.items():
            results += find_key(v, key)
    elif isinstance(obj, list):
        for item in obj:
            results += find_key(item, key)
    return results


def remove_duplicates(input_list):
    """
    Removes dictionaries with duplicate key-value pairs from a list of dictionaries.
    """
    output_list = []
    seen_pairs = set()
    for d in input_list:
        pairs = tuple(sorted(d.items()))
        if pairs not in seen_pairs:
            output_list.append(d)
            seen_pairs.add(pairs)
    return output_list


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
        json.dump(file_data, file, indent=4, ensure_ascii=False)