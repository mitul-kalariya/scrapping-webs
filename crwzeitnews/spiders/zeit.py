"""Spider to scrap ZEIT news website"""
import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime

import scrapy
from scrapy.http import XmlResponse
from scrapy.loader import ItemLoader
from scrapy.selector import Selector

from crwzeitnews.constant import (
    TODAYS_DATE,
    LOGGER,
)
from crwzeitnews import exceptions
from crwzeitnews.items import ArticleData
from crwzeitnews.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    get_request_headers,
)

# create log file
create_log_file()

class BaseSpider(ABC):
    """Abstract Base class for scrapy spider

    Args:
        ABC : Abstract
    """
    # pylint disable=unnecessary-pass
    @abstractmethod
    def parse(self,response):
        """parse function responsible for calling individual methods for each request"""
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        """called by parse function when response is sitemap"""
        pass

    def parse_sitemap_article(self, response: str) -> None:
        """called by parse function when response is sitemap article"""
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        """called by parse function when response is article"""
        pass


class ZeitSpider(scrapy.Spider, BaseSpider):
    """main spider for parsing sitemap or article"""
    # pylint: disable=too-many-instance-attributes
    name = "zeit"

    def __init__(self, *args, type=None, since=None, url=None, until=None, **kwargs):
        # pylint: disable=redefined-builtin
        """
        A spider to crawl globalnews.ca for news articles.
        The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca
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
            self.start_urls.append("https://www.zeit.de/gsitemaps/index.xml")
            self.since = datetime.strptime(since, "%Y-%m-%d").date() if until else None
            self.until = datetime.strptime(until, "%Y-%m-%d").date() if until else None
            validate_sitemap_date_range(since, until)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise exceptions.InvalidInputException("Must have a URL to scrap")

        # collecting request headers from target website index page
        request_headers = get_request_headers()
        self.valid_cookie = request_headers.get("cookie")
        self.valid_request_headers = request_headers
        self.start_requests()

    def start_requests(self):
        yield scrapy.Request(
            self.start_urls[0],
            headers=self.valid_request_headers,
            cookies=self.valid_cookie,
            callback=self.parse,
        )

    def parse(self, response, **kwargs):
        """
        Parses the given Scrapy response based on the specified type of parsing.

        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.

        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        if self.type == "sitemap":
            if self.since and self.until:
                LOGGER.info("Parse function called on %s", response.url)
                yield scrapy.Request(
                    response.url,
                    headers=self.valid_request_headers,
                    cookies=self.valid_cookie,
                    callback=self.parse_sitemap,
                    dont_filter=True,
                )
            else:
                yield scrapy.Request(
                    response.url,
                    headers=self.valid_request_headers,
                    cookies=self.valid_cookie,
                    callback=self.parse_sitemap,
                    dont_filter=True,
                )

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

        except Exception as exception:
            LOGGER.info(
                "Error occurred while scrapping an article for this link %s %s",
                response.url, str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def parse_sitemap(self, response) -> None:
        try:            # Create an XmlResponse object from the response
            xmlresponse = XmlResponse(
                url=response.url, body=response.body, encoding="utf-8"
            )
            # Create a Selector object from the XmlResponse
            xml_selector = Selector(xmlresponse)
            # Define the XML namespaces used in the sitemap
            xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            links = xml_selector.xpath(
                "//xmlns:loc/text()", namespaces=xml_namespaces
            ).getall()

            # Loop through each sitemap URL in the XML response
            for link in links:
                pub_date = (re.search(r"\d{4}-\d{2}-\d{2}", link)).group(0)
                published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()

                if self.since is None and self.until is None:
                    if TODAYS_DATE == published_at:
                        yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            meta={"link": link, "pub_date": published_at},
                            dont_filter=True,
                        )
                elif (
                    self.since
                    and self.until
                    and self.since <= published_at <= self.until
                ):
                    yield scrapy.Request(
                        link,
                        callback=self.parse_sitemap_article,
                        meta={"link": link, "pub_date": published_at},
                        dont_filter=True,
                    )

        except exceptions.SitemapScrappingException as exception:
            LOGGER.error("Error while parsing sitemap: %s",str(exception))
            print(f"Error while parsing sitemap: {str(exception)}")

    def parse_sitemap_article(self, response) -> None:
        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.
        Yields:
            scrapy.Request: A request object with the link and published date as metadata.
            The request object is sent to the 'parse_sitemap_link_title'
            callback function for further processing.
        """
        try:
            xmlresponse = XmlResponse(
                url=response.url, body=response.body, encoding="utf-8"
            )
            xml_selector = Selector(xmlresponse)
            xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            links = xml_selector.xpath(
                "//xmlns:loc/text()", namespaces=xml_namespaces
            ).getall()
            for link in links:
                data = {
                    "link": link,
                }
                self.articles.append(data)
        except exceptions.SitemapScrappingException as exception:
            LOGGER.error("Error while parsing sitemap article: %s", str(exception))
            raise exceptions.SitemapArticleScrappingException(
                f"Error while parsing sitemap article: {str(exception)}"
            )

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
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except BaseException as exception:
            LOGGER.log(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
