import scrapy
import logging
from dateutil import parser
from datetime import datetime
from newton_scrapping.constants import SITEMAP_URL, TODAYS_DATE, LOGGER
from newton_scrapping import exceptions
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from newton_scrapping.items import ArticleData
from newton_scrapping.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
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


class RepublicTvSpider(scrapy.Spider, BaseSpider):
    name = "republic_tv"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
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
        self.start_urls = []
        self.articles = []
        self.articles_url = url
        self.type = type.lower()

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(SITEMAP_URL)
            self.start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )
            validate_sitemap_date_range(start_date, end_date)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Error while")
                raise exceptions.InvalidInputException("Must have a URL to scrap")

    def parse(self, response):
        """
        Parses the response obtained from a website.

        Yields:
        scrapy.Request: A new request object to be sent to the website.

        Raises:
        BaseException: If an error occurs during parsing.
        """
        try:
            self.logger.info("Parse function called on %s", response.url)
            if self.type == "sitemap":
                if self.start_date and self.end_date:
                    self.logger.info("Parse function called on %s", response.url)
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
                else:
                    self.logger.info("Parse function called on %s", response.url)
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            print(f"Error while parse function: {e}")
            self.logger.error(f"Error while parse function: {e}")

    def parse_sitemap(self, response):
        """
        Parses a webpage response object and yields scrapy requests for each sitemap XML link found.

        Yields:
        scrapy.Request: A scrapy request object for each sitemap XML link found in the response.
        """
        try:
            self.logger.info("Parse Sitemap at %s", response.url)
            if "sitemap.xml" in response.url:
                for sitemap in response.xpath(
                    "//sitemap:loc/text()",
                    namespaces={
                        "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"
                    },
                ):
                    if sitemap.get().endswith(".xml"):
                        for link in sitemap.getall():
                            if self.start_date is None and self.end_date is None:
                                if str(TODAYS_DATE).replace("-", "") in link:
                                    yield scrapy.Request(
                                        link, callback=self.parse_sitemap_article
                                    )
                            else:
                                yield scrapy.Request(
                                    link, callback=self.parse_sitemap_article
                                )
        except BaseException as e:
            LOGGER.error("Error while parsing sitemap: {}".format(e))
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):
        """
        Parses a sitemap and sends requests to scrape each of the links.

        Yields:
        scrapy.Request: A request to scrape each of the links in the sitemap.

        Notes:
        The sitemap must be in the XML format specified by the sitemaps.org protocol.
        The function extracts the links from the sitemap
            and sends a request to scrape each link using the `parse_sitemap_link_title` callback method.
        The function also extracts the publication date of the sitemap, if available, and
            passes it along as a meta parameter in each request.
        """
        try:
            namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            links = response.xpath(
                "//n:url/n:loc/text()", namespaces=namespaces
            ).getall()
            published_at = response.xpath('//*[local-name()="lastmod"]/text()').get()
            published_date = parser.parse(published_at).date() if published_at else None
            for link in links:
                yield scrapy.Request(
                    link,
                    callback=self.parse_sitemap_by_link_title,
                    meta={"link": link, "published_date": published_date},
                )
        except BaseException as e:
            exceptions.SitemapArticleScrappingException(
                f"Error while parse sitemap article: {e}"
            )
            LOGGER.error(f"Error while parse sitemap article: {e}")

    def parse_sitemap_by_link_title(self, response):
        """
        Parses the link, title, and published date from a sitemap page.

        Notes:
        - Adds the parsed data to the scraper's sitemap_data list.
        - Skips the link if the published date is outside the scraper's specified date range.
        """
        try:
            link = response.meta["link"]
            published_date = response.meta["published_date"]
            title = response.css(".story-title::text").get().strip()

            if self.start_date and published_date < self.start_date:
                return
            if self.end_date and published_date > self.end_date:
                return

            data = {"link": link, "title": title}

            self.articles.append(data)
        except BaseException as e:
            exceptions.SitemapArticleScrappingException(
                f"Error while parse sitemap article: {e}"
            )
            LOGGER.error(f"Error while parse sitemap article: {e}")

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
        articledata_loader = ItemLoader(item=ArticleData(), response=response)
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        response_data["country"] = ["India"]
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
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while writing json file{str(exception)} - {reason}",
                level=logging.ERROR,
            )
