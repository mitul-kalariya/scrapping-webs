"""Spider to scrap terra news article"""
import logging
import requests
import json
from datetime import datetime, date
from abc import ABC, abstractmethod
import scrapy
from scrapy.http import XmlResponse
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from crwskytg24.constant import LINK_FEED, LOGGER
from crwskytg24.items import ArticleData
from crwskytg24 import exceptions
from crwskytg24.utils import (
    create_log_file,
    validate_sitemap_date_range,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    export_data_to_json_file,
)

# create log file
create_log_file()


class BaseSpider(ABC):
    """Abstract Base class for scrapy spider

    Args:
        ABC : Abstract
    """

    # pylint: disable=unnecessary-pass
    @abstractmethod
    def parse(self, response: str) -> None:
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


class SkyTg24Spider(scrapy.Spider, BaseSpider):
    """main spider for parsing sitemap or article"""

    name = "skytg24"

    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        # pylint: disable=redefined-builtin
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
            super().__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.proxies = kwargs.get("args", {}).get("proxies", None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()
            self.current_year = str(date.today().year)
            self.proxies = kwargs.get("args", {}).get("proxies", None)

            if self.type == "sitemap":
                self.start_urls.append(LINK_FEED)

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
            LOGGER.info(
                "Error occured in init function in %s:-- %s", self.name, exception
            )
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

    def parse(self, response, **kwargs):
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

        except BaseException as exception:
            LOGGER.info("Error occured in parse function: %s", exception)
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
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
                "Error occurred while scrapping an article for this link %s. %s",
                response.url,
                str(exception),
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def parse_sitemap(self, response):
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error while parsing the sitemap page.
        """  # pylint: disable=line-too-long
        try:
            today_date = date.today()
            start = 40
            boolean_start = True
            while boolean_start is True:
                end = start+20
                response_json = requests.request("GET", response.url+"/_jcr_content/root/infinite.model."+str(start)+"."+str(end)+".json")
                article_data = json.loads(response_json.text)
                start =end
                for article in article_data["cardList"]:
                    if boolean_start == True:
                        for data in article:
                            publish_date = data["editorialPublishedDate"]
                            article_pub_date = datetime.fromtimestamp(publish_date / 1000).date()
                            # data_dict = {}
                            # data_dict["title"] = j["title"]
                            # data_dict["url"] = j["url"]
                            # data_dict["date"] = str(article_date)
                            
                            if self.since and article_pub_date < self.since:
                                boolean_start =False
                                break
                            if self.since and article_pub_date > self.until:
                                boolean_start =False
                                break

                            if self.since and self.until:
                                link_data = {"link": data["url"], "title": data["title"]}
                                self.articles.append(link_data)
                            elif today_date == article_pub_date:
                                link_data = {"link": data["url"], "title": data["title"]}
                                self.articles.append(link_data)
                            else:
                                boolean_start = False
                                break
                    else:
                        break    
                        
        except BaseException as exception:
            LOGGER.info("Error while parsing sitemap: %s", exception)
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    # def parse_sitemap_article(self, response):
    #     """Extracts article titles and links from the response object and
    #     yields a Scrapy request for each article.
    #     Args:
    #         self: The Scrapy spider instance calling this method.
    #         response: The response object obtained after making a request to a sitemap URL.
    #     Yields:
    #         A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
    #         method as the callback and the article link and title as metadata.
    #     Raises:
    #         SitemapArticleScrappingException: If an error occurs while filtering articles by date.
    #     """
    #     try:
    #         namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    #         links = response.xpath("//n:loc/text()", namespaces=namespaces).getall()
    #         for link in links:
    #             today = date.today().strftime("%Y/%m/%d")
    #             start = link.find(self.current_year)
    #             pub_date = link[start:start + 10]
    #             published_at = datetime.strptime(pub_date, "%Y/%m/%d").date()
    #             if self.since and published_at < self.since:
    #                 continue
    #             if self.since and published_at > self.until:
    #                 continue

    #             if self.since and self.until:
    #                 data = {"link": link, "date": str(published_at)}
    #                 self.articles.append(data)
    #             elif today == pub_date:
    #                 data = {"link": link, "date": str(published_at)}
    #                 self.articles.append(data)
                
    #     except Exception as exception:
    #         LOGGER.info("Error while parsing sitemap article: %s", str(exception))
    #         raise exceptions.SitemapArticleScrappingException(
    #             f"Error while parsing sitemap article::-  {str(exception)}"
    #         )

    def closed(self, reason: any) -> None:
        """
        Method called when the spider is finished scraping.
        Saves the scraped data to a JSON file with a timestamp
        in the filename.
        """
        try:
            stats = self.crawler.stats.get_stats()
            if (
                stats.get(
                    "downloader/exception_type_count/scrapy.core.downloader.handlers.http11.TunnelError",
                    0,
                )
                > 0
            ) or (
                stats.get(
                    "downloader/request_count",
                    0,
                )
                == stats.get(
                    "downloader/exception_type_count/twisted.internet.error.TimeoutError",
                    0,
                )
            ):
                self.output_callback("Error in Proxy Configuration")
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                LOGGER.info("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            LOGGER.info(
                "Error occurred while writing json file %s - %s", str(exception), reason
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
