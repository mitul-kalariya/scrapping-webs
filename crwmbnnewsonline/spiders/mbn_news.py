import logging
from datetime import datetime
from abc import ABC, abstractmethod
import scrapy
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from scrapy.exceptions import CloseSpider

from crwmbnnewsonline.items import ArticleData

from crwmbnnewsonline.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file
)
from crwmbnnewsonline.exceptions import (
    SitemapScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
    InvalidArgumentException
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    filename="logs.log",
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


class Mbn_news(scrapy.Spider, BaseSpider):
    name = "mbn_news"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': 'http://www.google.com/schemas/sitemap-news/0.9'}

    def __init__(
        self, type=None, start_date=None,
        end_date=None, url=None, *args, **kwargs
    ):
        try:
            super(Mbn_news, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.article_url = url
            self.url = url
            self.error_msg_dict = {}
            self.start_date = start_date
            self.end_date = end_date
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
            raise InvalidArgumentException(
                f"Error occurred while taking type, url, start_date and end_date args.:- {str(exception)}")

    def parse(self, response):
        """
        Parses the given `response` object and extracts sitemap URLs or sends a
        request for articles based on the `type` attribute of the class instance.
        If `type` is "sitemap", extracts sitemap URLs from the XML content of the response and sends a request for
        each of them to Scrapy's engine with the callback function `parse_sitemap`.
        If `type` is "articles", sends a request for the given URL to Scrapy's engine
        with the callback function `parse_article`.
        This function is intended to be used as a Scrapy spider callback function.
        :param response: A Scrapy HTTP response object containing sitemap or article content.
        :return: A generator of Scrapy Request objects, one for each sitemap or article URL found in the response.
        """
        if response.status != 200:
            raise CloseSpider(
                f"Unable to scrape due to getting this status code {response.status}"
            )
        if self.type == "sitemap":
            try:
                sitemap_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                    namespaces=self.namespace).getall()

                for site_map_url in sitemap_urls:
                    yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

            except Exception as exception:
                self.log(
                    f"Error occured while iterating sitemap url. {str(exception)}",
                    level=logging.ERROR,
                )

        elif self.type == "article":
            try:
                yield self.parse_article(response)
            except Exception as exception:
                self.log(
                    f"Error occured while iterating article url. {str(exception)}",
                    level=logging.ERROR,
                )

    def parse_sitemap(self, response):
        """
           Parses the sitemap and extracts the article URLs and their last modified date.
           If the last modified date is within the specified date range, sends a request to the article URL
           :param response: the response from the sitemap request
           :return: scrapy.Request object
           """
        article_url = Selector(response, type='xml').\
            xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        mod_date = Selector(response, type='xml')\
            .xpath('//news:publication_date/text()',
                   namespaces=self.namespace).getall()
        article_titles = Selector(response, type='xml')\
            .xpath('//news:title/text()',
                   namespaces=self.namespace).getall()
        try:
            for url, date, title in zip(article_url, mod_date, article_titles):
                _date = datetime.strptime(date.split("T")[0].strip(), '%Y-%m-%d')
                if self.today_date:
                    if _date == self.today_date:

                        if title:
                            article = {
                                "link": url,
                                "title": title
                            }
                            self.articles.append(article)
                else:
                    if self.start_date <= _date <= self.end_date:

                        if title:
                            article = {
                                "link": url,
                                "title": title
                            }
                            self.articles.append(article)

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
        # Extract the article title from the response
        pass

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
            articledata_loader.add_value(
                "parsed_json",
                parsed_json_data,
            )
            articledata_loader.add_value(
                "parsed_data", get_parsed_data(response, parsed_json_dict)
            )
            self.articles.append(dict(articledata_loader.load_item()))
            return self.articles[0]

        except Exception as exception:
            self.log(
                f"Error occurred while fetching article details:- {str(exception)}",
                level=logging.ERROR,
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            ) from exception

    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            reason: generated reason
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

        except Exception as exception:
            self.log(
                f"Error occurred while closing crawler:- {str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while closing crawler:- {str(exception)} - {reason}"
            ) from exception
