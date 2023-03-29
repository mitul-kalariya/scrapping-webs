import logging
from datetime import datetime
from abc import ABC, abstractmethod
import scrapy
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

from crwlinternaute.items import ArticleData

from crwlinternaute.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file
)
from crwlinternaute.exceptions import (
    SitemapScrappingException,
    SitemapArticleScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
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


class Linternaute(scrapy.Spider, BaseSpider):
    name = "linternaute"
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9','news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(
        self, type=None, start_date=None,
        end_date=None, url=None, *args, **kwargs
                ):
        super(Linternaute, self).__init__(*args, **kwargs)
        self.output_callback = kwargs.get('args', {}).get('callback', None)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.url = url
        self.article_url = url
        self.start_date = start_date  # datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = end_date  # datetime.strptime(end_date, '%Y-%m-%d')
        self.today_date = None

        check_cmd_args(self, self.start_date, self.end_date)

    def parse(self, response):
        """
        Parses the given `response` object and extracts sitemap URLs or sends a
        request for articles based on the `type` attribute of the class instance.
        If `type` is "sitemap", extracts sitemap URLs from the XML content of the response and sends a request for each of them to Scrapy's engine with the callback function `parse_sitemap`.
        If `type` is "articles", sends a request for the given URL to Scrapy's engine with the callback function `parse_article`.
        This function is intended to be used as a Scrapy spider callback function.
        :param response: A Scrapy HTTP response object containing sitemap or article content.
        :return: A generator of Scrapy Request objects, one for each sitemap or article URL found in the response.
        """
        if self.type == "sitemap":

            site_map_url = Selector(response, type='xml')\
                            .xpath('//sitemap:loc/text()',
                                    namespaces=self.namespace).getall()

            mod_date = Selector(response, type='xml')\
                .xpath('//sitemap:lastmod/text()',
                       namespaces=self.namespace).getall()
            try:
                for url, date in zip(site_map_url, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')

                    if not self.today_date:
                        if self.start_date <= _date <= self.end_date:
                 
                            yield scrapy.Request(
                                url, callback=self.parse_sitemap)
                    else:
                        if self.today_date == _date:
                            yield scrapy.Request(
                                url, callback=self.parse_sitemap)

            except Exception as e:
                self.logger.exception(f"Error in parse_sitemap:- {e}")
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
        article_urls = Selector(response, type='xml').\
            xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        mod_date = Selector(response, type='xml')\
            .xpath('//sitemap:lastmod/text()',
                    namespaces=self.namespace).getall()

        try:
            for url, date in zip(article_urls, mod_date):
                _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                if self.today_date:
                    if _date == self.today_date:
                        if "ville" not in url and "television" not in url and "account" not in url:
                            yield scrapy.Request(
                                url, callback=self.parse_sitemap_article)
                else:
                    
                    if self.start_date <= _date <= self.end_date:
                        if "ville" not in url and "television" not in url and "account" not in url:
                            yield scrapy.Request(
                                url, callback=self.parse_sitemap_article)
                        
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
            # Extract the article title from the response
            title = response.css('div.entry h1::text').get()
            type_of_news = response.css('header.cp_diapo-header').get()
            # If the title exists, add the article information to the list of articles
            if title and not type_of_news:
                article = {
                    "link": response.url,
                    "title": title
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
                parsed_json_dict['ImageGallery'] = parsed_json_main
                parsed_json_dict['VideoObject'] = parsed_json_main
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
                "parsed_data", get_parsed_data(self, response, parsed_json_dict)
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
                f"Error occurred while exporting file:- {str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while exporting file:- {str(exception)} - {reason}"
            ) from exception
