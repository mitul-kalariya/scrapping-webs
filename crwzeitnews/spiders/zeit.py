import re

from scrapy import spiders
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
import scrapy
import logging
from dateutil import parser
from datetime import datetime

from scrapy.crawler import CrawlerProcess
from scrapy.http import XmlResponse
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from scrapy.utils.project import get_project_settings

from crwzeitnews.constant import (
    TODAYS_DATE,
    LOGGER,
    BASE_URL,
    SITEMAP_URL,
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


class ZeitSpider(scrapy.Spider, BaseSpider):
    name = "zeit"

    def __init__(self, type=None, since=None, url=None, until=None, *args, **kwargs):
        """
        A spider to crawl globalnews.ca for news articles. The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super(ZeitSpider, self).__init__(*args, **kwargs)

        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()
        create_log_file()
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
                raise Exception("Must have a URL to scrap")

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
        if self.type == "sitemap":
            if self.since and self.until:
                breakpoint()
                LOGGER.info("Parse function called on %s", response.url)
                yield scrapy.Request(
                    response.url,
                    headers=self.valid_request_headers,
                    cookies=self.valid_cookie,
                    callback=self.parse_sitemap,
                    dont_filter = True,
                )
            else:
                breakpoint()
                yield scrapy.Request(
                    response.url,
                    headers=self.valid_request_headers,
                    cookies=self.valid_cookie,
                    callback=self.parse_sitemap,
                    dont_filter = True,
                )

        elif self.type == "article":

            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            yield articledata_loader.item

    def parse_article(self, response: str) -> list:
        pass

    def parse_sitemap(self, response, **kwargs) -> None:
        try:
            print("\n\n\n\n\n\n\n +++++++++++++++++++++++++++++++++++++++++++++++++")
        
            # Create an XmlResponse object from the response
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

                if self.since and published_at < self.since:
                    return

                if self.since and published_at > self.until:
                    return

                if self.since is None and self.until is None:
                    if TODAYS_DATE == published_at:
                        yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            meta={"link": link, "pub_date": published_at},
                            dont_filter = True,
                        )
                else:
                    if self.since and self.until:
                        yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            meta={"link": link, "pub_date": published_at},
                            dont_filter = True,
                        )

        except exceptions.SitemapScrappingException as exception:
            LOGGER.error(f"{str(exception)}")
            print(f"Error while parsing sitemap: {str(exception)}")

    def parse_sitemap_article(self, response) -> None:
        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.
        Yields:
            scrapy.Request: A request object with the link and published date as metadata.
            The request object is sent to the 'parse_sitemap_link_title' callback function for further processing.
        """
        try:

            xmlresponse = XmlResponse(
                url=response.url, body=response.body, encoding="utf-8"
            )
            xml_selector = Selector(xmlresponse)
            xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            links = xml_selector.xpath("//xmlns:loc/text()", namespaces=xml_namespaces).getall()
            for link in links:
                data = {
                    "link": link,
                }
                self.articles.append(data)
        except exceptions.SitemapScrappingException as exception:
            LOGGER.error(f"Error while parsing sitemap article: {str(exception)}")
            exceptions.SitemapArticleScrappingException(
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
    process.crawl()
    process.start()
