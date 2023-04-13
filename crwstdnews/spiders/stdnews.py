"""Spider to scrap STD.stheadline news website"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
import requests

import scrapy
from scrapy.loader import ItemLoader

from crwstdnews.constant import (
    LINK_FEED_URL,
    BASE_URL,
    LOGGER,
)
from crwstdnews import exceptions
from crwstdnews.items import ArticleData
from crwstdnews.utils import (
    create_log_file,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)

# create logs
create_log_file()


class BaseSpider(ABC):
    """Abstract Base class for scrapy spider
    Args:
        ABC : Abstract
    """

    @abstractmethod
    def parse(self, response):
        """
        Parses the given Scrapy response based on the specified type of parsing.

        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.

        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.
        Yields:
            scrapy.Request: A request object with the link and published date as metadata.
            The request object is sent to the 'parse_sitemap_link_title'
            callback function for further processing.
        """
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.

        Args:
            response (scrapy.http.Response): The response object containing the article data.

        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        pass


class STDNewsSpider(scrapy.Spider, BaseSpider):
    """main spider class for STD news"""

    name = "stdnews"
    start_urls = [BASE_URL]

    def __init__(self, *args, type=None, url=None, **kwargs):
        # pylint: disable=redefined-builtin
        """
        A spider to crawl std.stheadline for news articles.
        The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of std.stheadline
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider.
                        Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode.
                              Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode.
                            Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super().__init__(*args, **kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()

        if self.type == "sitemap":
            self.start_urls.append(LINK_FEED_URL)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise exceptions.InvalidInputException("Must have a URL to scrap")

        self.request_headers = {
            "authority": "std.stheadline.com",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "dnt": "1",
            "origin": "https://std.stheadline.com",
            "referer": "https://std.stheadline.com/realtime/%E5%8D%B3%E6%99%82",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",  # noqa: E501
            "x-requested-with": "XMLHttpRequest",
        }

    def parse(self, response, **kwargs):
        """
        Parses the given Scrapy response based on the specified type of parsing.

        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.

        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        if self.type == "sitemap":
            self.parse_sitemap(response)
        elif self.type == "article":
            article_data = self.parse_article(response)
            yield article_data

    def parse_article(self, response: str) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.

        Args:
            response (scrapy.http.Response): The response object containing the article data.

        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        try:
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response = get_raw_response(response)
            response_json = get_parsed_json(response)
            response_data = get_parsed_data(response)
            response_data["time_scraped"] = [str(datetime.now())]
            articledata_loader.add_value("raw_response", raw_response)
            articledata_loader.add_value(
                "parsed_json",
                response_json,
            )
            articledata_loader.add_value("parsed_data", response_data)

            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item

        except Exception as exception:
            LOGGER.info(
                "Error occurred while scrapping an article for this link %s %s",
                response.url,
                str(exception),
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def parse_sitemap(self, response):
        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.
        Yields:
            scrapy.Request: A request object with the link and published date as metadata.
            The request object is sent to the 'parse_sitemap_link_title'
            callback function for further processing.
        """
        today_flag = True
        page_counter = 1
        while today_flag is True:
            response_json = (
                requests.request(
                    "POST",
                    LINK_FEED_URL,
                    headers=self.request_headers,
                    data="page=" + str(page_counter),
                    timeout=5,
                )
            ).json()
            article_list = response_json.get("data")
            for article_data in article_list:
                if "\u65e5\u524d" in article_data.get("publish_datetime"):
                    today_flag = False
                    break
                self.articles.append(
                    {
                        "link": article_data.get("articleLink"),
                        "title": article_data.get("title").get("tc"),
                    }
                )
            page_counter += 1

    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            reason: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """
        try:
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except BaseException as exc:
            LOGGER.log(
                f"Error occurred while closing crawler{str(exc)} - {reason}",
                level=logging.ERROR,
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exc)} - {reason}"
            )
