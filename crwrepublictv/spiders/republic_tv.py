import scrapy
import logging
from datetime import datetime
from crwrepublictv.constant import SITEMAP_URL, TODAYS_DATE, LOGGER
from crwrepublictv import exceptions
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from crwrepublictv.items import ArticleData
from crwrepublictv.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)

from scrapy.http import XmlResponse
from scrapy.selector import Selector


# create log file
create_log_file()

class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class RepublicTvSpider(scrapy.Spider, BaseSpider):
    name = "republic_tv"

    def __init__(self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs):
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
        try:
            super(RepublicTvSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()

            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)
                self.start_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else TODAYS_DATE
                )
                self.end_date = (
                    datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else TODAYS_DATE
                )

                validate_sitemap_date_range(start_date, end_date)

            if self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.error("Error while")
                    raise exceptions.InvalidInputException("Must have a URL to scrap")
        except BaseException as exception:
            LOGGER.info(f"Error occured in init function in {self.name}:-- {exception}")
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

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

        except BaseException as exception:
            LOGGER.info(f"Error occured in parse function: {exception}")
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_sitemap(self, response):

        """
        Parses a webpage response object and yields scrapy requests for each sitemap XML link found.

        Yields:
        scrapy.Request: A scrapy request object for each sitemap XML link found in the response.
        """
        try:
            xmlresponse = XmlResponse(
                url=response.url, body=response.body, encoding="utf-8"
            )
            # Create a Selector object from the XmlResponse
            xml_selector = Selector(xmlresponse)
            # Define the XML namespaces used in the sitemap
            xml_namespaces = {"xmlns": "https://www.sitemaps.org/schemas/sitemap/0.9"}
            # Loop through each sitemap URL in the XML response
            links = xml_selector.xpath('//*[local-name()="loc"]/text()', namespaces=xml_namespaces).getall()
            titles = xml_selector.xpath('//*[local-name()="title"]/text()', namespaces=xml_namespaces).getall()
            published_dates = xml_selector.xpath('//*[local-name()="publication_date"]/text()', namespaces=xml_namespaces).getall()


            for link, title, pub_date in zip(links, titles, published_dates):
                published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
                data = {"link": link, "title": title}
                if self.start_date is None and self.end_date is None:
                    if TODAYS_DATE == published_at:
                        self.articles.append(data)
                elif (
                        self.start_date
                        and self.end_date
                        and self.start_date <= published_at <= self.end_date
                ):
                    self.articles.append(data)
                elif self.start_date and self.end_date:
                    if published_at == self.start_date and published_at == self.end_date:
                        self.articles.append(data)
        except BaseException as exception:
            LOGGER.error("Error while parsing sitemap: {}".format(exception))
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {exception}")


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
            response_data["source_country"] = ["India"]
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
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def closed(self, reason: any) -> None:
        """
        Method called when the spider is finished scraping.
        Saves the scraped data to a JSON file with a timestamp
        in the filename.
        """
        try:
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                LOGGER.info("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            LOGGER.info(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while writing json file {str(exception) - {reason}}"
            )

