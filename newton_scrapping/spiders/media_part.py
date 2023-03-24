import re
import json
from typing import Dict, Any

import scrapy
import requests
import logging
from datetime import datetime
from io import BytesIO
from PIL import Image
from scrapy.http import XmlResponse
from scrapy.selector import Selector
from newton_scrapping import exceptions
from newton_scrapping.constants import BASE_URL, TODAYS_DATE, LOGGER
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
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


class MediaPartSpider(scrapy.Spider, BaseSpider):
    name = "media_part"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
        A spider to crawl mediapart.fr for news articles.
        The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of mediapart.fr
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super().__init__(**kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type.lower()

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append("https://www.mediapart.fr/sitemap_index.xml")
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
                LOGGER.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")


    def parse(self, response):
        """
        Parse the response and extract data based on the spider's type and configuration.

        Yields:
            If the spider's type is "sitemap" and a start and
                end date are specified, a request is yielded to parse by date.
            If the spider's type is "article", a dictionary of parsed data is appended to the article_json_data list.

        Raises:
            BaseException: If an error occurs during parsing, an error is logged and printed to the console.
        """
        try:
            self.logger.info("Parse function called on %s", response.url)
            if self.type == "sitemap":
                if self.start_date and self.end_date:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
                else:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
                article_data = self.parse_article(response)
                self.articles.append(article_data)

        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")


    def parse_article(self,response):
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
        response_data["country"] = ["Germany"]
        response_data["time_scraped"] = [str(datetime.now())]

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        return dict(articledata_loader.load_item())

    def parse_sitemap(self, response):
        """
        Function to parse a sitemap response by date

        Returns:
            Yields scrapy.Request objects for each link found in the sitemap.

        Description:
        This function takes in a scrapy response object and parses it by date to extract the sitemap links.
        For each sitemap link found, it yields a scrapy.Request object to the parse_sitemap function.

        """
        try:
            # Create an XmlResponse object from the response
            xmlresponse = XmlResponse(
                url=response.url, body=response.body, encoding="utf-8"
            )
            # Create a Selector object from the XmlResponse
            xml_selector = Selector(xmlresponse)
            # Define the XML namespaces used in the sitemap
            xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            # Loop through each sitemap URL in the XML response
            for sitemap in xml_selector.xpath(
                "//xmlns:loc/text()", namespaces=xml_namespaces
            ):
                # Loop through each link in the sitemap and create a scrapy request for it
                for link in sitemap.getall():
                    yield scrapy.Request(link, callback=self.parse_sitemap_article)
        # If there's any error during the above process, log it and print
        except BaseException as e:
            LOGGER.error("Error while parsing sitemap: {}".format(e))
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):

        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.

        Yields:
            scrapy.Request: A request object with the link and published date as metadata.
            The request object is sent to the 'parse_sitemap_link_title' callback function for further processing.
        """
        try:
            # Define the namespace for the sitemap
            namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Extract the links and published dates from the sitemap
            links = response.xpath("//n:loc/text()", namespaces=namespaces).getall()
            published_date = response.xpath(
                '//*[local-name()="lastmod"]/text()'
            ).getall()

            # Loop through the links and published dates
            for link, pub_date in zip(links, published_date):
                # Convert the published date to a datetime object
                published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()

                # Convert today's date to a datetime object
                # today_date = datetime.strptime(TODAYS_DATE, "%Y-%m-%d").date()

                # If the published date falls within the specified date range, make a request to the link
                if (
                    self.start_date
                    and self.end_date
                    and self.start_date <= published_at <= self.end_date
                ):
                    yield scrapy.Request(
                        link,
                        callback=self.parse_sitemap_by_title_link,
                        meta={"link": link, "published_date": published_at},
                    )

                # If the published date is today's date, make a request to the link
                elif TODAYS_DATE == published_at:
                    yield scrapy.Request(
                        link,
                        callback=self.parse_sitemap_by_title_link,
                        meta={"link": link, "published_date": published_at},
                    )
                else:
                    continue
                    # If there's any error during the above process, log it and print
        except BaseException as e:
            LOGGER.error(f"Error while parsing sitemap article: {e}")
            exceptions.SitemapArticleScrappingException(f"Error while parsing sitemap article: {e}")

    def parse_sitemap_by_title_link(self, response):
        try:
            link = response.meta["link"]
            published_date = response.meta["published_date"]
            title = response.css("h1#page-title::text").get()
            if self.start_date and published_date < self.start_date:
                return
            if self.start_date and published_date > self.end_date:
                return
            data = {
                "link": link,
                "title": title,
            }
            if title:
                self.articles.append(data)
        except BaseException as e:
            LOGGER.error(f"Error while parsing sitemap article: {e}")
            exceptions.SitemapArticleScrappingException(f"Error while parsing sitemap article: {e}")

    def parse_article(self, response) -> dict[Any, Any]:
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
        response_data["country"] = ["France"]
        response_data["time_scraped"] = [str(datetime.now())]

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        return dict(articledata_loader.load_item())






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


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(MediaPartSpider)
    process.start()