import logging
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
import scrapy

from datetime import datetime, timedelta
from crwleparisien.items import ArticleData
from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector

from crwleparisien.exceptions import (
    SitemapScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
)
from crwleparisien.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
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
    def parse_article(self, response: str) -> list:
        pass


class LeParisien(scrapy.Spider, BaseSpider):
    name = "le_parisien"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': 'http://www.google.com/schemas/sitemap-news/0.9'}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        try:
            super(LeParisien, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.start_date = start_date
            self.end_date = end_date
            self.article_url = url
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
            raise SitemapScrappingException(
                f"Error occurred while iterating sitemap url:- {str(exception)}"
            ) from exception

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
        try:
            if response.status != 200:
                raise CloseSpider(
                    f"Unable to scrape due to getting this status code {response.status}"
                )
            if self.type == "sitemap":
                # for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                #                                                          namespaces=self.namespace).getall():
                #     yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
                yield scrapy.Request(response.url, callback=self.parse_archive)

            elif self.type == "article":
                yield self.parse_article(response)
        except Exception as exception:
            self.log(
                f"Error occurred while iterating {self.type} url. {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while iterating {self.type} url:- {str(exception)}"
            ) from exception

    def parse_archive(self, response):  # noqa:C901

        try:
            if self.today_date:
                if self.today_date.day < 10 and self.today_date.month < 10:
                    url = f"{response.url}{self.today_date.year}/0{self.today_date.day}-0{self.today_date.month}-{self.today_date.year}"  # noqa:E501
                elif self.today_date.day >= 10 and self.today_date.month < 10:
                    url = f"{response.url}{self.today_date.year}/{self.today_date.day}-0{self.today_date.month}-{self.today_date.year}"  # noqa:E501
                elif self.today_date.day < 10 and self.today_date.month >= 10:
                    url = f"{response.url}{self.today_date.year}/0{self.today_date.day}-{self.today_date.month}-{self.today_date.year}"  # noqa:E501
                else:
                    url = f"{response.url}{self.today_date.year}/0{self.today_date.day}-{self.today_date.month}-{self.today_date.year}"  # noqa:E501
                yield scrapy.Request(url, callback=self.parse_archive_article)

            else:
                date_range = [self.start_date + timedelta(days=x)
                              for x in range((self.end_date - self.start_date).days + 2)]
                for date in date_range:
                    if date.day < 10 and date.month < 10:
                        url = f"{response.url}{date.year}/0{date.day}-0{date.month}-{date.year}"
                    elif date.day >= 10 and date.month < 10:
                        url = f"{response.url}{date.year}/{date.day}-0{date.month}-{date.year}"
                    elif date.day < 10 and date.month >= 10:
                        url = f"{response.url}{date.year}/0{date.day}-{date.month}-{date.year}"
                    else:
                        url = f"{response.url}{date.year}/{date.day}-{date.month}-{date.year}"
                    yield scrapy.Request(url, callback=self.parse_archive_article)

        except Exception as exception:
            self.log(
                f"Error occurred while iterating sitemap url. {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while iterating sitemap url:- {str(exception)}"
            ) from exception

    def parse_archive_article(self, response):
        try:

            urls_selector = response.css('.story-preview')
            for selector in urls_selector:
                title = selector.css('span::text').get()
                link = selector.css('a::attr("href")').get()
                self.articles.append({"link": link[0], "title": title})
        except Exception as exception:
            self.log(
                f"Error occurred while archive articles url. {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while archive articles url. {str(exception)}"
            ) from exception

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

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """

        try:
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            parsed_json_dict = {}

            parsed_json_main = response.css('script[type="application/ld+json"]::text')
            parsed_json_misc = response.css('script[type="application/json"]::text')
            if parsed_json_main:
                parsed_json_dict["main"] = parsed_json_main
                parsed_json_dict['imageObjects'] = parsed_json_main
                parsed_json_dict['videoObjects'] = parsed_json_main
                parsed_json_dict['other'] = parsed_json_main

            if parsed_json_misc:
                parsed_json_dict["misc"] = parsed_json_misc

            parsed_json_data = get_parsed_json(response, parsed_json_dict)
            articledata_loader.add_value("raw_response", raw_response)
            if parsed_json_data:
                articledata_loader.add_value(
                    "parsed_json",
                    parsed_json_data,
                )
            articledata_loader.add_value(
                "parsed_data", get_parsed_data(response, parsed_json_dict)
            )

            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item

        except Exception as exception:
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
            if self.output_callback is not None:
                self.output_callback(self.articles)
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
