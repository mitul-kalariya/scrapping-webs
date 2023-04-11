from abc import ABC, abstractmethod
import logging
import scrapy
from datetime import datetime
from crweconomist.itemLoader import ArticleDataLoader
from crweconomist.items import ArticleData
from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from crweconomist.exceptions import (
    ArticleScrappingException,
    ExportOutputFileException,
    SitemapScrappingException,
)
from crweconomist.utils import (
    check_cmd_args,
    get_parsed_data,
    get_parsed_json,
    get_raw_response
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    filename="economist_canada.log",
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
    def parse_article(self, response: str) -> list:
        pass


class Economist(scrapy.Spider, BaseSpider):
    name = "economist_canada"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        try:
            super(Economist, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.error_msg_dict = {}
            self.url = url
            self.article_url = url
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
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse(self, response):
        try:
            if response.status != 200:
                raise CloseSpider(
                    f"Unable to scrape due to getting this status code {response.status}"
                )
            if self.type == "sitemap":
                for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                         namespaces=self.namespace).getall()[4:]:
                    if self.today_date:
                        if self.today_date.year <= int(site_map_url.split('-')[-2]) <= self.today_date.year:
                            yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
                    else:
                        if self.start_date.year <= int(site_map_url.split('-')[-2]) <= self.end_date.year:
                            yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
            if self.type == "article":
                yield self.parse_article(response)

        except Exception as exception:
            self.log(
                f"Error occurred while iterating sitemap url. {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse_sitemap(self, response):
        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        mod_date = Selector(response, type='xml').xpath('//sitemap:lastmod/text()', namespaces=self.namespace).getall()
        try:
            if self.today_date:
                for url, date in zip(article_urls, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if _date == self.today_date:
                        self.articles.append({"link": url})
            else:
                for url, date in zip(article_urls, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if self.start_date <= _date <= self.end_date:
                        self.articles.append({"link": url})
        except Exception as exception:
            self.log(
                f"Error occurred while fetching sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse_article(self, response):
        try:
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(raw_response_dict)
            articledata_loader = ArticleDataLoader(item=ArticleData())
            parsed_json_dict = {}

            parsed_json_main = response.css('script[type="application/ld+json"]::text')
            parsed_json_misc = response.css('script[type="application/json"]::text')

            if parsed_json_main:
                parsed_json_dict["main"] = parsed_json_main
                parsed_json_dict['ImageGallery'] = parsed_json_main
                parsed_json_dict['videoObjects'] = parsed_json_main
                parsed_json_dict['imageObjects'] = parsed_json_main
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
                "parsed_data", get_parsed_data(response, parsed_json_data)
            )
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item
        except Exception as exception:
            self.logger.exception(
                f"Error occurred while fetching article details:- {str(exception)}"
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            ) from exception

    def closed(self, reason):
        try:
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)

        except Exception as exception:
            self.log(
                f"Error occurred while exporting file:- {str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while exporting file:- {str(exception)} - {reason}"
            ) from exception
