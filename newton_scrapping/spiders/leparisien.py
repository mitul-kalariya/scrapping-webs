import logging
from abc import ABC, abstractmethod
from newton_scrapping.itemLoader import ArticleDataLoader
import scrapy

from datetime import datetime
from newton_scrapping.items import ArticleData
from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector

from newton_scrapping.exceptions import (
    SitemapScrappingException,
    SitemapArticleScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
)
from newton_scrapping.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    filename="leparisien.log",
    filemode="a",
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
    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class LeParisien(scrapy.Spider, BaseSpider):
    name = "le_parisien"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': 'http://www.google.com/schemas/sitemap-news/0.9'}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        try:
            super(LeParisien, self).__init__(*args, **kwargs)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.start_date = start_date
            self.end_date = end_date
            self.url = url
            self.error_msg_dict = {}
            self.today_date = None
            check_cmd_args(self, self.start_date, self.end_date)
        except Exception as exception:
            self.error_msg_dict["error_msg"] = (
                "Error occurred while taking type, url, start_date and end_date args. " + str(exception)
            )
            self.log(
                "Error occurred while taking type, url, start_date and end_date args. " + str(exception),
                level=logging.ERROR,
            )

    def parse(self, response):
        """
            Parses the response of a scrapy.Request and yields further requests or items.

            If the `type` attribute of the spider is set to "sitemap", the method looks for all the sitemap URLs in the
            response (assuming it's an XML file) and yields a scrapy.Request for each of them, using the `parse_sitemap`
            method as the callback for each request.

            If the `type` attribute of the spider is set to "article", the method yields a scrapy.Request for the URL
            specified in the `url` attribute of the spider,
            using the `parse_article` method as the callback for the request.

            :param response: the response of the current request.
            """
        if response.status != 200:
            raise CloseSpider(
                f"Unable to scrape due to getting this status code {response.status}"
            )
        if self.type == "sitemap":
            try:
                for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                         namespaces=self.namespace).getall():
                    yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
            except Exception as exception:
                self.log(
                    f"Error occurred while iterating sitemap url. {str(exception)}",
                    level=logging.ERROR,
                )

        elif self.type == "article":
            try:
                yield self.parse_article(response)
            except Exception as exception:
                self.log(
                    f"Error occured while parsing article url. {str(exception)}",
                    level=logging.ERROR,
                )

    def parse_sitemap(self, response):
        """
           Parses the sitemap and extracts the article URLs and their last modified date.
           If the last modified date is within the specified date range, sends a request to the article URL
           :param response: the response from the sitemap request
           :return: scrapy.Request object
        """
        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        published_date = Selector(response, type='xml').xpath('//news:publication_date/text()',
                                                              namespaces=self.namespace).getall()
        title = Selector(response, type='xml').xpath('//news:title/text()', namespaces=self.namespace).getall()
        try:
            if self.start_date is not None and self.end_date is not None:
                for article, date, title in zip(article_urls, published_date, title):
                    if self.start_date <= datetime.strptime(date.split('T')[0], '%Y-%m-%d') <= self.end_date:
                        self.logger.info('Fetching sitemap data for given date range  ------------')
                        article = {
                            "link": article,
                            "title": title,
                        }
                        self.articles.append(article)

            elif self.start_date is None and self.end_date is None:
                for article, date, title in zip(article_urls, published_date, title):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if _date == self.today_date:
                        self.logger.info("Fetching today's sitemap data ------------")
                        article = {
                            "link": article,
                            "title": title,
                        }
                        self.articles.append(article)

            elif self.start_date is None or self.end_date is None:
                raise ValueError("start_date and end_date both required.")
            else:
                raise ValueError("Invalid date range")
        except Exception as exception:
            self.log(
                f"Error occurred while fetching sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse_sitemap_article(self, response):
        """
        Parse article information from a given sitemap URL.

        :param response: HTTP response from the sitemap URL.
        :return: None
        """
        try:
            title = response.css('#top > header > h1::text').getall()
            if title:
                article = {
                    "link": response.url,
                    "title": title,
                }
                self.articles.append(article)
        except Exception as exception:
            self.log(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapArticleScrappingException(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}"
            ) from exception

    def parse_article(self, response):
        """
            This function takes the response object of the news article page and extracts the necessary information
            using get_article_data() function and constructs a dictionary using set_article_dict() function
            :param response: scrapy.http.Response object
            :return: None
        """
        try:
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader = ArticleDataLoader(item=ArticleData())
            parsed_json_dict = {}

            parsed_json_main = response.css('script[type="application/ld+json"]::text')
            parsed_json_misc = response.css('script[type="application/json"]::text')

            if parsed_json_main:
                parsed_json_dict["main"] = parsed_json_main
                parsed_json_dict['ImageGallery'] = parsed_json_main
                parsed_json_dict['VideoObject'] = parsed_json_main
                parsed_json_dict['other'] = parsed_json_main

            if parsed_json_misc:
                parsed_json_dict["misc"] = parsed_json_misc

            parsed_json_data = get_parsed_json(parsed_json_dict)
            articledata_loader.add_value("raw_response", raw_response)
            if parsed_json_data:
                articledata_loader.add_value(
                    "parsed_json",
                    parsed_json_data,
                )
            articledata_loader.add_value(
                "parsed_data", get_parsed_data(self, response, parsed_json_data)
            )
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item
        except Exception as exception:
            self.logger.exception(
                f"Error occurred while fetching article details:- {str(exception)}"
            )
            self.log(
                f"Error occurred while fetching article details:- {str(exception)}",
                level=logging.ERROR,
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            ) from exception

    def closed(self, reason):
        """
            This function is executed when the spider is closed. It saves the data scraped
            by the spider into a JSON file with a filename based on the spider type and
            the current date and time.
            :param reason: the reason for the spider's closure
            """
        try:
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            self.log(
                f"Error occurred while exporting file:- {str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while exporting file:- {str(exception)} - {reason}"
            ) from exception
