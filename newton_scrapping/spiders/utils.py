import re
import requests
import logging
from PIL import Image
from io import BytesIO
from datetime import datetime

# Setting the threshold of logger to DEBUG
LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"

logging.basicConfig(
    level=logging.DEBUG,
    filename="logs.log",
    format=LOG_FORMAT,
    filemode="a",
)

# Creating an object
logger = logging.getLogger()


class InvalidDateRange(Exception):
    pass


def parse_sitemap_main(self, start_urls, start_date, end_date):
    start_urls.append("https://www.republicworld.com/sitemap.xml")
    try:
        start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        if start_date and not end_date:
            raise ValueError("end_date must be specified if start_date is provided")
        if not start_date and end_date:
            raise ValueError("start_date must be specified if end_date is provided")
        if start_date and end_date and start_date > end_date:
            raise InvalidDateRange("start_date should not be later than end_date")
        if start_date and end_date and start_date == end_date:
            raise ValueError("start_date and end_date must not be the same")
    except ValueError as e:
        logger.error(f"Error in __init__: {e}")
        raise InvalidDateRange(f"{e}")


def response_data(response):
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
    main_dict = {}
    authors = extract_author(response)
    main_dict["author"] = authors
    last_updated = extract_lastupdated(response)
    main_dict["modified_at"] = [last_updated]
    published_on = extract_published_on(response.css("div.story-wrapper"))
    main_dict["published_at"] = [published_on]
    description = response.css("h2.story-description::text").get()
    main_dict["description"] = [description]
    publisher = extract_publisher(response)
    main_dict["publisher"] = publisher
    article_text = response.css("section p::text").getall()
    main_dict["text"] = [" ".join(article_text)]
    thumbnail = extract_thumbnail(response)
    main_dict["thumbnail_image"] = thumbnail
    headline = response.css("h1.story-title::text").get().strip()
    main_dict["title"] = [headline]
    article_images = extract_all_images(response)
    main_dict["images"] = article_images
    video = extract_video(response)
    main_dict["embed_video_link"] = video
    article_lang = response.css("html::attr(lang)").get()
    main_dict["language"] = [article_lang]
    return filter_dict(main_dict)


def filter_dict(raw_dict):
    """
        Filtering null value from the dictionary
    """
    target_dict = dict([(vkey, vdata) for vkey, vdata in raw_dict.items() if (vdata)])
    return target_dict


def extract_lastupdated(response) -> str:
    """
    This function extracts the last updated date and time of an article from a given Scrapy response object.
    It returns a string representation of the date and time in ISO 8601 format.
    If the information is not available in the response, it returns None.

    Args:
        response: A Scrapy response object representing the web page from which to extract the information.
    """
    info = response.css("span.time-elapsed")
    if info:
        return info.css("time::attr(datetime)").get()


def extract_published_on(response) -> str:
    info = response.xpath('//div[@class ="padtop10 padbtm10"]')
    info_eng = response.css("div.padtop20")

    if info:
        return info.css("time::attr(datetime)").get()
    elif info_eng:
        return info_eng.css("time::attr(datetime)").get()


def extract_author(response) -> list:
    """
    The extract_author function extracts information about the author(s)
    of an article from the given response object and returns it in the form of a list of dictionaries.

    Parameters:
        response (scrapy.http.Response): The response object containing the HTML of the article page.

    Returns:
        A list of dictionaries, where each dictionary contains information about one author.

    """
    info = response.css("div.author")
    pattern = r"[\r\n\t\"]+"
    data = []
    if info:
        for i in info:
            temp_dict = {}
            temp_dict["@type"] = "Person"
            temp_dict["name"] = re.sub(
                pattern, "", i.css("div a span::text").get()
            ).strip()
            temp_dict["url"] = i.css("div a::attr(href)").get()
            data.append(temp_dict)
        return data


def extract_thumbnail(response) -> list:
    """
    The function extract_thumbnail extracts information about the thumbnail image(s) associated with a webpage,
    including its link, width, and height, and returns the information as a list of dictionaries.

    Returns:
        A list of dictionaries, with each dictionary containing information about an image.
            If no images are found, an empty list is returned.
    """
    info = response.css("div.gallery-item")
    mod_info = response.css(".storypicture img.width100")
    data = []
    if info:
        for i in info:
            image = i.css("div.gallery-item-img-wrapper img::attr(src)").get()
            if image:
                data.append(image)
    elif mod_info:
        for i in mod_info:
            image = i.css("img::attr(src)").get()
            if image:
                data.append(image)
    return data


def extract_video(response) -> list:
    """
    A list of video objects containing information about the videos on the webpage.
    """
    info = response.css("div.videoWrapper")
    data = []
    if info:
        for i in info:
            js = i.css("script").get()
            request_link = re.findall(r"playlist\s*:\s*'(\S+)'", js)[0]
            response = requests.get(request_link)
            link = response.json().get("playlist")[0].get("sources")[1].get("file")
            temp_dict = {"link": link}
            data.append(temp_dict)
    return data


def extract_publisher(response) -> list:
    """
    Extracts publisher information from the given response object and returns it as a dictionary.

    Returns:
    - A dictionary containing information about the publisher. The dictionary has the following keys:
        - "@id": The unique identifier for the publisher.
        - "@type": The type of publisher (in this case, always "NewsMediaOrganization").
        - "name": The name of the publisher.
    """
    logo = response.css('link[rel="icon"]::attr(href)').getall()[2]
    img_response = requests.get(logo)
    width, height = Image.open(BytesIO(img_response.content)).size
    a_dict = {
        "@id": "bharat.republicworld.com",
        "@type": "NewsMediaOrganization",
        "name": "Bharat republic word",
        "logo": {
            "@type": "ImageObject",
            "url": logo,
            "width": {"@type": "Distance", "name": str(width) + " px"},
            "height": {"@type": "Distance", "name": str(height) + " px"},
        },
    }
    return [a_dict]


def extract_all_images(response) -> list:
    """
    Extracts all the images present in the web page.

    Returns:
    list: A list of dictionaries containing information about each image,
    such as image link.
    """
    info = response.css("div.embedpicture")
    data = []
    if info:
        for i in info:
            temp_dict = {}
            image = i.css("div.embedimgblock img::attr(src)").get()
            if image:
                temp_dict["link"] = image
            data.append(temp_dict)
    return data
