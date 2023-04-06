import logging
from abc import ABC, abstractmethod
from datetime import datetime

import scrapy
from scrapy.loader import ItemLoader

from crwhk01 import exceptions
from crwhk01.constant import LOGGER, SITEMAP_URL, TODAYS_DATE
from crwhk01.items import ArticleData
from crwhk01.utils import (
    create_log_file,
    export_data_to_json_file,
    get_parsed_data,
    get_parsed_json,
    get_raw_response,
    validate_sitemap_date_range,
)


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


class HK01Spider(scrapy.Spider, BaseSpider):
    name = "hk01"

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
        super(HK01Spider, self).__init__(*args, **kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.type = type.lower()
        self.main_json = None
        self.article_url = url

        create_log_file()

        if self.type == "sitemap":
            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)
                self.since = (
                    datetime.strptime(since, "%Y-%m-%d").date()
                    if since
                    else TODAYS_DATE
                )
                self.until = (
                    datetime.strptime(until, "%Y-%m-%d").date()
                    if until
                    else TODAYS_DATE
                )
                validate_sitemap_date_range(since, until)
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

        except BaseException as exception:
            LOGGER.info(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:- {str(exception)}"
            )

    def parse_article(self, response) -> list:
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
            response_data["source_country"] = ["China"]
            response_data["time_scraped"] = [str(datetime.now())]

            articledata_loader.add_value("raw_response", raw_response)
            articledata_loader.add_value(
                "parsed_json",
                response_json,
            )
            articledata_loader.add_value("parsed_data", response_data)
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item
        except BaseException as exception:
            LOGGER.info(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:- {str(exception)}"
            )

    def parse_sitemap(self, response):
        try:
            namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            url = response.xpath("//xmlns:url", namespaces=namespaces)
            links = url.xpath("xmlns:loc/text()", namespaces=namespaces).getall()
            titles = url.xpath('//*[local-name()="title"]/text()').getall()
            published_date = url.xpath(
                '//*[local-name()="publication_date"]/text()'
            ).getall()

            for link, title, pub_date in zip(links, titles, published_date):
                published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
                data = {"link": link, "title": title}
                if self.since is None and self.until is None:
                    if TODAYS_DATE == published_at:
                        self.articles.append(data)
                elif (
                    self.since
                    and self.until
                    and self.since <= published_at <= self.until
                ):
                    self.articles.append(data)
                elif self.since and self.until:
                    if published_at == self.since and published_at == self.until:
                        self.articles.append(data)

        except BaseException as exception:
            LOGGER.error(f"Error while parsing sitemap: {str(exception)}")
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_sitemap_article(self, response):
        pass

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
            # else:
            #     export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            LOGGER.error(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
