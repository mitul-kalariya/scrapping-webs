# Utility/helper functions
# utils.py

import json
import logging
from datetime import datetime
from crwmetropoles import exceptions
from crwmetropoles.constant import TODAYS_DATE, LOGGER
import itertools


def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_sitemap_date_range(start_date, end_date):
    start_date = (
        datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    )
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    try:
        if start_date and not end_date:
            raise exceptions.InvalidDateException(
                "end_date must be specified if start_date is provided"
            )
        if not start_date and end_date:
            raise exceptions.InvalidDateException(
                "start_date must be specified if end_date is provided"
            )

        if start_date and end_date and start_date > end_date:
            raise exceptions.InvalidDateException(
                "start_date should not be later than end_date"
            )

        if start_date and end_date and start_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "start_date should not be greater than today_date"
            )

        if start_date and end_date and end_date > TODAYS_DATE:
            raise exceptions.InvalidDateException(
                "end_date should not be greater than today_date"
            )

    except exceptions.InvalidDateException as expception:
        LOGGER.info(f"Error occured while checking date range: {expception}")
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
        main = response.css('script[type="application/ld+json"]::text').getall()
        for block in main:
            data.append(json.loads(block))
        return data
    except BaseException as exception:
        LOGGER.info(f"Error occured while fetching main: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while fetching main: {exception}"
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


def get_raw_response(response):
    """
    Raw response data generated from given response and selector

    Args:
        response: provided response
        selector_and_key: A dictionary with key and selector

    Returns:
        Dictionary with generated raw response
    """

    raw_resopnse = {
        "content_type": response.headers.get("Content-Type").decode("utf-8"),
        "content": response.text,
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
        imageObjects = []
        videoObjects = []
        other_data = []
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
        for a_block in ld_json_data:
            data = json.loads(a_block)
            json_data = data.get("@graph")
            for main_data in json_data:
                if main_data.get("@type") == "NewsArticle":
                    parsed_json["main"] = main_data
                elif main_data.get("@type") in {"ImageGallery", "ImageObject"}:
                    imageObjects.append(data)
                elif main_data.get("@type") == "VideoObject":
                    videoObjects.append(data)
                else:
                    other_data.append(main_data)

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
    """
    Extracts data from a news article webpage and returns it in a dictionary format.
    Parameters:
    response (scrapy.http.Response): A scrapy response object of the news article webpage.
    Returns:
    dict: A dictionary containing the extracted data from the webpage, including:
         - 'publisher': (str) The name of the publisher of the article.
         - 'article_catagory': The region of the news that the article refers to
         - 'headline': (str) The headline of the article.
         - 'authors': (list) The list of authors of the article, if available.
         - 'published_on': (str) The date and time the article was published.
         - 'updated_on': (str) The date and time the article was last updated, if available.
         - 'text': (list) The list of text paragraphs in the article.
         - 'images': (list) The list of image URLs in the article, if available. (using bs4)
    """
    try:
        main_dict = {}
        publisher = get_publisher(response)
        main_dict["publisher"] = publisher

        headline = response.css("div.m-head-single h1::text").getall()
        main_dict["title"] = headline

        authors = get_author(response)
        main_dict["author"] = authors

        description = response.css("meta[name='description']::attr(content)").getall()
        main_dict["description"] = description

        data = get_main(response)
        # breakpoint()
        for main_data in data:
            for block in main_data.get("@graph"):
                if "datePublished" in block:
                    main_dict["published_at"] = [block.get("datePublished")]
                if "dateModified" in block:
                    main_dict["modified_at"] = [block.get("dateModified")]

        section = get_section(response)
        main_dict["section"] = section

        thumbnail_image = get_thumbnail_image(response)
        main_dict["thumbnail_image"] = thumbnail_image

        article_text = response.css(
            "article.m-content p::text, article.m-content p a::text, article.m-content p strong::text").getall()

        main_dict["text"] = [" ".join(article_text)]

        tags = get_tags(response)
        main_dict["tags"] = [tags]

        images = get_images(response)
        if images:
            main_dict["images"] = images

        main_dict["embed_video_link"] = response.css("iframe::attr(src)").getall()[1:]
        main_dict["source_language"] = ["Portuguese"]

        main_dict["source_country"] = ["Brazil"]
        main_dict["time_scraped"] = [str(datetime.now())]

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )


def get_publisher(response):
    """
    Extracts publisher information from the given response object and returns it as a dictionary.
    Returns:
    - A dictionary containing information about the publisher.The dictionary has the following keys:
    ---
    @id: The unique identifier for the publisher.
    @type: The type of publisher (in this case, always "NewsMediaOrganization").
    name: The name of the publisher.
    logo: Logo of the publisher as an image object
    """
    try:
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
        for a_block in ld_json_data:
            json_loads = json.loads(a_block)
            data = []
            for block in json_loads.get("@graph"):
                if "publisher" in block.keys():
                    data.append(block.get("publisher"))
                    return data

    except Exception as exception:
        LOGGER.info(f"Error while fetching publisher data {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching publisher data {str(exception)}"
        )


def get_author(response) -> list:
    """
    The get_author function extracts information about the author(s)
    of an article from the given response object and returns it in the form of a list of dictionaries.
    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        A list of dictionaries, where each dictionary contains information about one author.
    """
    try:
        parsed_data = response.css('script[type="application/ld+json"]::text').getall()
        for a_block in parsed_data:
            for data in json.loads(a_block).get("@graph"):
                author_data = []
                if data.get("@type") == "NewsArticle":
                    if "author" in data.keys():
                        author_data.append(data.get("author"))
                        return author_data

    except Exception as exception:
        LOGGER.info(f"Error while fetching author {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching author {str(exception)}"
        )


def get_section(response) -> list:
    """
    This functions finds the section from the response
    and returns the articleSection list
    """
    try:
        section_data = get_main(response)
        for section in section_data:
            for block in section.get("@graph"):
                articleSection = []
                if "articleSection" in block:
                    articleSection.append(block.get("articleSection"))
                    return articleSection
    except Exception as exception:
        LOGGER.info(f"Error while fetching section {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching section {str(exception)}"
        )


def get_thumbnail_image(response) -> list:
    """extracting thumbnail image from application+ld/json data in main function
    Args:
        response (obj): page_object
    Returns:
        list: list of thumbnail images
    """
    try:
        image_data = get_main(response)
        for image in image_data:
            for block in image.get("@graph"):
                if "image" in block.keys():
                    thumbnail_image = [block.get("image").get("url")]
                    return thumbnail_image
    except Exception as exception:
        LOGGER.info(f"Error while fetching thumbnail image {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching thumbnail image {str(exception)}"
        )


def get_tags(response) -> list:
    """
    Extracts lables associated to the news article in form of a list of dictionary
    containing name of the tag and the corrosponding link to the tag
    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.
    Returns:
        a list of dictionary with link and name combination
    """
    try:
        info = response.css("div.c-tags__body a")
        data = []
        for i in info:
            temp_dict = {}
            temp_dict["tag"] = i.css("a::text").get()
            temp_dict["url"] = i.css("a::attr(href)").get()
            if temp_dict["url"] == "#":
                pass
            else:
                data.append(temp_dict)
        return data
    except Exception as exception:
        LOGGER.info(f"Error while fetching tags {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching tags {str(exception)}"
        )


def get_images(response) -> list:
    """extracting image links from provided response
    Args:
        response (_type_): html page object
    Returns:
        list: list of images inside the article
    """
    try:
        picture_links = response.css(
            "article figure img::attr(src), div.m-image-carousel img::attr(data-src)"
        ).getall()
        captions = response.css(
            "article figure figcaption, div.siema-item > div.m-subtitle-carousel p"
        )
        captions_list = []

        for caption in captions:
            cap_text = ""
            text = caption.css("*::text").getall()
            if text:
                for i in text:
                    cap_text += i.strip()
            else:
                cap_text = None
            captions_list.append(cap_text)

        temp_dict = {
            "images": [
                {"link": img, "caption": cap}
                for img, cap in itertools.zip_longest(
                    picture_links,
                    captions_list,
                    fillvalue=None,
                )
            ]
        }
        return temp_dict.get("images")

    except Exception as exception:
        LOGGER.info(f"Error while fetching image {str(exception)}")
        raise exceptions.ArticleScrappingException(
            f"Error while fetching image {str(exception)}"
        )
