import logging
from abc import ABC, abstractmethod
from datetime import datetime

import scrapy
from scrapy.loader import ItemLoader

from crwbbcnews.constant import BASE_URL, TODAYS_DATE, LOGGER, SITEMAP_URL
from crwbbcnews.exceptions import (
    ArticleScrappingException,
    ExportOutputFileException,
    ParseFunctionFailedException,
    SitemapScrappingException,
    InvalidInputException
)
from crwbbcnews.items import ArticleData
from crwbbcnews.utils import (
    create_log_file,
    get_data_from_json,
    get_parsed_json,
    get_raw_response,
    validate_sitemap_date_range,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Creating an object
logger = logging.getLogger()


class BaseSpider(ABC):
    @abstractmethod
    def parse(self, response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class BBCNews(scrapy.Spider, BaseSpider):
    name = "bbc"

    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object with the given parameters.
        Parameters:
        type (str): The type of scraping to be performed. Either "sitemap" or "article".
        sinde (str): The start date of the time period to be scraped, in the format "YYYY-MM-DD".
        url (str): The URL of the article to be scraped. Required if type is "article".
        until (str): The end date of the time period to be scraped, in the format "YYYY-MM-DD".
        **kwargs: Additional keyword arguments to be passed to the superclass constructor.
        Raises:
        ValueError: If the since date and/or until date are invalid.
        InvalidDateRange: If the since is later than the until date.
        Exception: If no URL is provided when type is "article".
        """
        super(BBCNews, self).__init__(*args, **kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.type = type.lower()
        self.main_json = None
        self.article_url = url

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(SITEMAP_URL)
            self.since = (
                datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
            )
            self.until = (
                datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
            )
            validate_sitemap_date_range(since, until)
        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise InvalidInputException("Must have a URL to scrap")

    def parse(self, response):
        """
        Parses the response obtained from a website.
        Yields:
        scrapy.Request: A new request object to be sent to the website.
        Raises:
        BaseException: If an error occurs during parsing.
        """
        self.logger.info("Parse function called on %s", response.url)
        try:
            if self.type == "sitemap":
                yield scrapy.Request(response.url, callback=self.parse_sitemap)
            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as exception:
            LOGGER.info(f"Error occured in parse function: {exception}")
            raise ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_sitemap(self, response):
        """
        Parses the sitemap and extracts the article URLs and their last modified date.
        If the last modified date is within the specified date range, sends a request to the article URL
        :param response: the response from the sitemap request
        :return: scrapy.Request object
        """
        try:
            groups = response.json()['content']['groups']
            for group in groups:
                group_types = group['items']
                for group_type in group_types:
                    article_timestamp = group_type['timestamp']
                    article_date = datetime.fromtimestamp(article_timestamp / 1000).date()

                    locators = group_type.get('locators')
                    if not locators:
                        continue
                    url = BASE_URL + str(locators.get("assetUri"))
                    article = {
                        "link": url,
                        "title": group_type['headlines']['headline']
                    }

                    if self.since is None and self.until is None:
                        if TODAYS_DATE == article_date:
                            self.articles.append(article)
                    elif (
                        self.since
                        and self.until
                        and self.since <= article_date <= self.until
                    ):
                        self.articles.append(article)
                    elif self.since and self.until:
                        if article_date == self.since and article_date == self.until:
                            self.articles.append(article)
        except BaseException as exception:
            LOGGER.error(f"Error while parsing sitemap: {str(exception)}")
            raise SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """
        try:
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            parsed_json_dict = {}

            parsed_json_main = response.css('script[type="application/ld+json"]::text')
            parsed_json_misc = response.css('script[type="application/json"]::text')

            if parsed_json_main:
                parsed_json_dict["main"] = parsed_json_main
                parsed_json_dict["imageObjects"] = parsed_json_main
                parsed_json_dict["videoObjects"] = parsed_json_main
                parsed_json_dict["other"] = parsed_json_main

            if parsed_json_misc:
                parsed_json_dict["misc"] = parsed_json_misc

            parsed_json_data = get_parsed_json(response, parsed_json_dict)
            articledata_loader.add_value("raw_response", raw_response)
            if parsed_json_data:
                articledata_loader.add_value(
                    "parsed_json",
                    parsed_json_data,
                )
            articledata_loader.add_value(
                "parsed_data", get_data_from_json(response, parsed_json_data)
            )
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item

        except BaseException as exception:
            LOGGER.info(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:- {str(exception)}"
            )

    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            reason: generated reason
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
        except BaseException as exception:
            LOGGER.error(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
