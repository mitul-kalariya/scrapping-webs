"""NDTV spider"""
import logging
from datetime import datetime,timedelta
from abc import ABC, abstractmethod
import scrapy

from scrapy.http import XmlResponse
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

from crwndtv import exceptions
from crwndtv.constant import SITEMAP_URL, LOGGER
from crwndtv.items import ArticleData
from crwndtv.utils import (
    validate_sitemap_date_range,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    export_data_to_json_file,
)



class BaseSpider(ABC):
    """
    Base class for making abstract methods
    """
    @abstractmethod
    def parse(self, response):
        # pylint disable=W0107
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
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object 
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error 
            while parsing the sitemap page.
        """
        pass

    def parse_sitemap_article(self, response: str) -> None:
        """Extracts article titles and links from the response object 
        and yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
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


class NDTVSpider(scrapy.Spider, BaseSpider):
    """Spider"""

    name = "ndtv"

    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.
        Args:
            type (str): A string indicating the type of data to scrape. Must be either
            "sitemap" or "article".
            since (str): A string representing the start date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            url (str): A string representing the URL of the webpage to be scraped.
            until (str): A string representing the end date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            **kwargs: Additional keyword arguments that can be used to pass 
            information to the web scraper.
        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.
        Notes:
            This function initializes a web scraper object and sets various 
            properties based on the arguments passed.
            If the type argument is "sitemap", the start and end dates of 
            the sitemap are validated and set.
            If the type argument is "article",
            the URL to be scraped is validated and set. A log file is created for the web scraper.
        """
        try:
            super(NDTVSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.date_range_lst = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()

            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)

                self.since = (
                    datetime.strptime(since, "%Y-%m-%d").date() if since else None
                )
                self.until = (
                    datetime.strptime(until, "%Y-%m-%d").date() if until else None
                )
                validate_sitemap_date_range(since, until)

            if self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.info("Must have a URL to scrap")
                    raise exceptions.InvalidInputException("Must have a URL to scrap")

        except Exception as exception:
            LOGGER.info("Error occured in init function in %s :-- %s",self.name,exception)
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

    def date_range(self, start_date, end_date):
        """
        return range of all date between given date
        if not end_date then take start_date as end date
        """
        try:
            for date in range(int((end_date - start_date).days) + 1):
                yield start_date + timedelta(date)
        except Exception as exception:
            self.log(
                "Error occured while generating date range. " + str(exception),
                level=logging.ERROR,
            )

    def parse(self, response):
        """
        Parses the given Scrapy response based on the specified type of parsing.
        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.
        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        try:
            if self.type == "sitemap":
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            LOGGER.info("Error occured in parse function: %s",e)
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {e}"
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
                "Error occurred while scrapping an article for this link %s.",response.url
                + str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def parse_sitemap(self, response):
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object 
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error 
            while parsing the sitemap page.
        """

        # self.logger.info("Parse function called on %s", response.url)
        if "sitemap.xml" in response.url:

            for single_date in self.date_range(self.since, self.until):

                try:
                    # url info : https://www.ndtv.com/sitemap.xml/?yyyy=2023&mm=04&dd=05&sitename=&category=
                    yield scrapy.Request(
                        f"https://www.ndtv.com/sitemap.xml/?yyyy={single_date.year}&mm={single_date.month}&dd={single_date.day}&sitename=&category=",
                        callback=self.parse_sitemap_article,
                    )

                except BaseException as e:
                    LOGGER.info("Error while parsing sitemap: %s",e)
                    raise exceptions.SitemapScrappingException(
                        f"Error while parsing sitemap: {str(e)}"
                    )

    def parse_sitemap_article(self, response):
        """Extracts article titles and links from the response object 
        and yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        try:
            namespaces = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            links = response.xpath(
                "//sitemap:loc/text()", namespaces=namespaces
            ).getall()
            published_date = response.xpath(
                "//sitemap:lastmod/text()", namespaces=namespaces
            ).getall()

            for link, pub_date in zip(links, published_date):
                # publish_date = pub_date.split("T")
                # published_at = datetime.strptime(publish_date[0], "%Y-%m-%d").date()
                # today_date = datetime.today().date()
                #
                # if self.since and published_at < self.since:
                #     return
                # if self.since and published_at > self.until:
                #     return

                if (
                    link != "https://www.ndtv.com/sitemap/google-news-sitemap"
                ):
                    data = {"link": link}
                    self.articles.append(data)
                # elif (
                #     today_date == published_at
                #     and link != "https://www.ndtv.com/sitemap/google-news-sitemap"
                # ):
                #     data = {"link": link}
                #     self.articles.append(data)
                else:
                    continue

        except Exception as exception:
            LOGGER.info("Error while parsing sitemap article: %s", str(exception))
            raise exceptions.SitemapArticleScrappingException(
                "Error while parsing sitemap article::%s-",str(exception))

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
                breakpoint()
        except BaseException as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )
        