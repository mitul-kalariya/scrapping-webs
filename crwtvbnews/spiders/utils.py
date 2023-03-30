import json
import logging

from scrapy.http import Response
from datetime import datetime


from ..selenium import Selenium
from selenium.common.exceptions import NoSuchElementException

logging.basicConfig(filename='selenium.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (ZeitDeNews): The ZeitDeNews spider instance.
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
    initial_url = "https://news.tvb.com/sitemap.xml"
    if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("Enter start_date and end_date for maximum 30 days.")
        else:
            self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
        today_time = datetime.today().strftime("%Y-%m-%d")
        self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
        self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:
        raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

    elif self.type == "article" and self.url is not None:
        self.start_urls.append(self.url)

    elif self.type == "article" and self.url is None:
        raise ValueError("type articles must be used with url")

    else:
        raise ValueError("type should be articles or sitemap")


def get_article_data(response: Response) -> dict:
    """
       Extracts relevant data from the response of the given URL
       :param response: The response object obtained from a HTTP request to the URL
       :return: A dictionary containing relevant article data.
       """
    sel = Selenium()
    sel.visit(response.url)
    # breakpoint()

    article_data = {}
    # article_data["title"] = response.css('div.newsEntryContainer h1::text').get()
    # article_data["text"] = response.css('h6.descContainer > pre::text').getall()
    try:
        article_data["text"] = sel.get_text()
        article_data["title"] = sel.get_title()
        # article_data["category"] = sel.get_category()
    except NoSuchElementException as e:
        logger.error(f"Couldn't find element - {e}")
    article_data["category"] = response.css('div.breadcrumbContainer a h5 font font::text').getall()
    selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
    misc_data = response.xpath('//script[@type="application/json"]/text()').getall()
    article_data["json_data"] = [json.loads(data) for data in selector]
    article_data["json_misc_data"] = [json.loads(misc) for misc in misc_data]
    # print(f'>>>>>> {article_data["text"]}')
    # exit()
    return article_data


def set_article_dict(response: Response, article_data: dict) -> dict:
    """
      Takes in a `Response` object and a dictionary containing article data, and returns a dictionary
      containing the article information in a standardized format.

      Args:
          response (requests.Response): A `Response` object containing the raw HTTP response data.
          article_data (dict): A dictionary containing the extracted article data.

      Returns:
          dict: A dictionary containing the article information in a standardized format. The
          dictionary contains three main sections: `raw_response`, `parsed_json`, and `parsed_data`.
          The `raw_response` section contains the raw response data from the HTTP request, while
          the `parsed_json` section contains the parsed JSON-LD data extracted from the article.
          The `parsed_data` section contains the article information extracted from the raw HTML data.
      """
    article = {
        'raw_response': {
            "content_type": response.headers.get("Content-Type").decode("utf-8"),
            "content": response.text,
        },
        "parsed_json": {
            "main": article_data.get('json_data'),
            "misc": article_data.get("json_misc_data")
        },
        "parsed_data": {
            "author": article_data.get("json_data")[0].get("author"),
            "description": article_data.get('json_data')[0].get("description"),
            "modified_at": article_data.get("json_data")[0]['dateModified'],
            "published_at": article_data.get("json_data")[0]['datePublished'],
            "publisher": {'@type': article_data.get("json_data")[0]['publisher']['@type'],
                          'name': article_data.get("json_data")[0]['publisher']['name'],
                          'url': article_data.get("json_data")[0]['publisher']['url'],
                          'logo': {
                              "@type": article_data.get("json_data")[0]['publisher']['logo']["@type"],
                              'width': {
                                  '@type': "Distance",
                                  "name": str(article_data.get("json_data")[0]['publisher']['logo']['width']) + " Px"},
                              'height': {
                                  '@type': "Distance",
                                  'name': str(
                                      article_data.get("json_data")[0]['publisher']['logo']['height']) + " Px"}},
                          "text": article_data.get("text"),
                          # "thumbnail_image": [article_data.get("img_url")],  # need to look it
                          "title": article_data.get("title"),
                          # "images": [{"link": article_data.get("img_url"), "caption": article_data.get(
                          # "img_caption")}], "video": {"link": video_link, "caption": None},
                          "section": "".join(article_data.get("category")).split(","),
                          # "tags": article_data.get("tags")
                          }
        }
    }
    return article
