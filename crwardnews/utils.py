# Utility/helper functions
# utils.py

import os
import re
import json
import logging
from datetime import datetime
from crwardnews import exceptions
from crwardnews.constant import TODAYS_DATE, BASE_URL, LOGGER


def create_log_file():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
        filename="logs.log",
        filemode="a",
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
        imageObjects = []
        videoObjects = []
        other_data = []
        ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
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

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting parsed json {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting parsed json {exception}"
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

def get_parsed_data(response):
    try:
        pattern = r"[\r\n\t\"]+"
        main_dict = get_parsed_data_dict()
        video = []
        main_data = get_main(response)
        article_json = main_data.get("article")
        videoobject_json = main_data.get("VideoObject")
        web_page = main_data.get("WebPage")
        if article_json:
            main_data = article_json
        elif videoobject_json:
            main_data = videoobject_json
        else:
            main_data = web_page

        # extract author and publisher information
        main_dict |= get_author_publisher(main_data, response)

        # extract the date published at
        main_dict |= get_description_dates(main_data,response)

        # extract the description or read text of the article
        text = response.css("p.textabsatz::text").getall()
        text = [re.sub(pattern, "", i) for i in text]
        if text:
            main_dict["text"] = ["".join(list(filter(None, text)))]

        # extract section information
        section = get_section(response)
        main_dict["section"] = section

        # extract the thumbnail image
        thumbnail_image = response.css(
            "picture.ts-picture--topbanner .ts-image::attr(src)"
        ).get()
        if thumbnail_image:
            main_dict["thumbnail_image"] = [BASE_URL + thumbnail_image]

        # get article images
        main_dict |= get_article_title_images(response)

        # extract video files if any
        frame_video = get_embed_video_link(response.css("div.copytext__video"))
        if frame_video:
            video.extend(frame_video)

        main_dict["embed_video_link"] = video

        # extract tags associated with article
        tags = response.css("ul.taglist li a::text").getall()
        main_dict["tags"] = tags

        mapper = {"de": "German"}
        article_lang = response.css("html::attr(lang)").get()
        main_dict["source_language"] = [mapper.get(article_lang)]

        return remove_empty_elements(main_dict)

    except Exception as exception:
        LOGGER.info(f"Error while extracting parsed data: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error while extracting parsed data: {exception}"
        )

def get_author_publisher(parsed_json_dict,response):
    if parsed_json_dict:
        return {
            "author":[parsed_json_dict.get("author",None)],
            "publisher":[parsed_json_dict.get("publisher",None)]
        }
    else:
        return {
            "author": [response.css("meta[name=\"author\"]::attr(content)").get()],
            "publisher": [{"name":response.css("meta[name=\"publisher\"]::attr(content)").get()}]
        }

def get_description_dates(parsed_json_dict,response):
    if parsed_json_dict:
        return {
            "published_at": [parsed_json_dict.get("datePublished",None)],
            "modified_at": [parsed_json_dict.get("dateModified",None)],
            "description": [parsed_json_dict.get("description",None)]
        }
    else:
        return {
            "published_at": [response.css("meta[name=\"date\"]::attr(content)").get()],
            "description": [response.css("meta[name=\"description\"]::attr(content)").get()],
        }

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


def get_embed_video_link(response) -> list:
    try:
        info = []
        for child in response:
            raw_video_json = child.css("div.ts-mediaplayer::attr(data-config)").get()
            video_json = (json.loads(raw_video_json)).get("mc")

            if video_json.get("_sharing"):
                video_link = video_json.get("_sharing").get("link")
                if video_link:
                    info.append(video_link)
            elif video_json.get("_download"):
                video_link = video_json.get("_download").get("url")
                if video_link:
                    info.append(video_link)
        return info

    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article video link: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting article video link: {exception}"
        )


def get_article_title_images(response) -> list:
    try:
        info = []
        title = []
        pattern = r"[\r\n\t\"]+"
        if response.css("div.absatzbild").get():
            for child in response.css("div.absatzbild"):
                a_dict = {}
                a_dict["link"] = (
                    BASE_URL
                    + child.css("div.absatzbild__media div picture img::attr(src)").get()
                )
                caption = re.sub(
                    pattern, "", child.css("div.absatzbild__info p::text").get()
                ).strip()
                if caption:
                    a_dict["caption"] = caption
                info.append(remove_empty_elements(a_dict))
            title.append(response.css("span.seitenkopf__headline--text::text").get())
        elif response.css("div[data-v-type=\"Slider\"]::attr(data-v)").get():
            images_dict = json.loads(response.css("div[data-v-type=\"Slider\"]::attr(data-v)").get())
            images = images_dict.get("images",None)
            if images:
                for image in images:
                    info.append(
                        {
                        "link":BASE_URL+image.get("url"),
                        "caption":image.get("description"),
                    })
            title.append(response.css("h1 .multimediahead__headline::text").get())

        return {"images":info,"title":title}
    except BaseException as exception:
        LOGGER.info(f"Error occured while getting article images: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while getting article images: {exception}"
        )


def get_section(response) -> list:
    try:
        breadcrumb_list = response.css("ul.article-breadcrumb li")
        for i in breadcrumb_list:
            text = i.css("li a::text").get()
            if text:
                text = text.split()
                text = "".join(text)
                if text:
                    return [text]

    except BaseException as exception:
        LOGGER.info(f"Error occured while extracting section: {exception}")
        raise exceptions.ArticleScrappingException(
            f"Error occured while extracting section: {exception}"
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
    try:
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

    except Exception as exception:
            LOGGER.info(f"Error occurred while writing json file {str(exception)}")
            raise exceptions.ArticleScrappingException(
            f"Error occurred while writing json file {str(exception)}"
            )


