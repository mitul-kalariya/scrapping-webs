import logging
from abc import ABC, abstractmethod
from datetime import datetime
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.loader import ItemLoader
from scrapy.utils.project import get_project_settings

from crwntv import exceptions
from crwntv.constant import LOGGER, SITEMAP_URL, TODAYS_DATE
from crwntv.items import ArticleData
from crwntv.utils import (create_log_file, get_parsed_data, get_parsed_json,
                          get_raw_response)


class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class NTvSpider(scrapy.Spider, BaseSpider):
    name = "n_tv"

    def __init__(self, type=None, url=None, start_date=None, end_date=None, **kwargs):
        """
        Initializes a web scraper object with the given parameters.

        Parameters:
        type (str): The type of scraping to be performed. Either "sitemap" or "article".
        start_date (str): The start date of the time period to be scraped, in the format "YYYY-MM-DD".
        url (str): The URL of the article to be scraped. Required if type is "article".
        end_date (str): The end date of the time period to be scraped, in the format "YYYY-MM-DD".
        **kwargs: Additional keyword arguments to be passed to the superclass constructor.

        Raises:
        ValueError: If the start_date and/or end_date are invalid.
        InvalidDateRange: If the start_date is later than the end_date.
        Exception: If no URL is provided when type is "article".
        """
        super().__init__(**kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.type = type.lower()
        self.article_url = url

        create_log_file()
        if self.type == "sitemap":
            if start_date is not None or end_date is not None:
                raise Exception("Date filter is not available")
            self.start_urls.append(SITEMAP_URL)
        elif self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                self.logger.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

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

        except BaseException as e:
            self.logger.error(
                f"Error occurring while parsing sitemap {e} in parse function"
            )

    def parse_sitemap(self, response):  # noqa: C901
        try:
            namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            loc = response.xpath("//xmlns:loc/text()", namespaces=namespaces).getall()
            title = response.xpath(
                "//*[local-name()='title' and namespace-uri()='http://www.google.com/schemas/sitemap-news/0.9']/text()"
            ).getall()
            published_date = response.xpath(
                "//*[local-name()='publication_date' and namespace-uri()='http://www.google.com/schemas/sitemap-news/0.9']/text()"  # noqa: E501
            ).getall()
            for loc, title, pub_date in zip(loc, title, published_date):
                if loc and title and pub_date:
                    published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
                    data = {"link": loc, "title": title}
                    if TODAYS_DATE == published_at:
                        self.articles.append(data)

        except BaseException as e:
            LOGGER.error(f"Error while parsing sitemap: {e}")
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):
        pass

    def parse_article(self, response):
        """
        Parses the article data from the response object and returns it as a dictionary.

        Args:
            response (scrapy.http.Response): The response object containing the article data.

        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """

        articledata_loader = ItemLoader(item=ArticleData(), response=response)
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        response_data["source_country"] = ["Germany"]
        response_data["time_scraped"] = [str(datetime.now())]
        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        self.articles.append(dict(articledata_loader.load_item()))
        return articledata_loader.item

    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            response: generated response
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
        except Exception as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(NTvSpider)
    process.start()
