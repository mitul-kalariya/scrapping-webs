import logging
from datetime import datetime
from abc import ABC, abstractmethod
import scrapy
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

from crwam730.items import ArticleData

from crwam730.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
)
from crwam730.exception import (
    ArticleScrappingException,
    SitemapScrappingException
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
    def parse_article(self, response: str) -> list:
        pass


class Am730(scrapy.Spider, BaseSpider):
    name = "am730"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(Am730, self).__init__(*args, **kwargs)
        self.output_callback = kwargs.get('args', {}).get('callback', None)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.url = url
        self.article_url = url
        self.start_date = start_date
        self.end_date = end_date
        self.today_date = None

        check_cmd_args(self, self.start_date, self.end_date)

    def parse(self, response):  # noqa:C901
        """
        This function is used to parse the response from a web page or a sitemap.
        Args:
            self: The spider object that calls this function.
            response: The response object returned by a web page or a sitemap.
        Returns:
            If the response is from a sitemap and contains article URLs within the desired time range
            (specified by the spider object's `start_date`, `end_date`, or `today_date` attributes),
            this function yields a request object for each article URL using the `parse_sitemap` callback.
            If the response is from an article URL, this function yields a request object for the article
            using the `parse_article` callback.
        """
        if self.type == "sitemap":
            article_url = Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                               namespaces=self.namespace).getall()
            published_date = Selector(response, type='xml').xpath('//news:publication_date/text()',
                                                                  namespaces=self.namespace).getall()
            article_title = Selector(response, type='xml').xpath('//news:title/text()',
                                                                 namespaces=self.namespace).getall()
            try:
                for url, date, title in zip(article_url, published_date, article_title):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if self.today_date:
                        if _date == self.today_date:
                            if title:
                                article = {
                                    "link": url,
                                    "title": title,
                                }
                                self.articles.append(article)
                    else:
                        if self.start_date <= _date <= self.end_date:
                            if title:
                                article = {
                                    "link": url,
                                    "title": title,
                                }
                                self.articles.append(article)
            except Exception as exception:
                self.log(
                    f"Error occurred while fetching sitemap:- {str(exception)}"
                )
                raise SitemapScrappingException(
                    f"Error occurred while fetching sitemap:- {str(exception)}"
                ) from exception

        if self.type == "article":
            try:
                yield self.parse_article(response)
            except Exception as exception:
                self.log(
                    f"Error occured while iterating article url. {str(exception)}"
                )
                raise ArticleScrappingException(f"Error occured while iterating article url. {str(exception)}")

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
            articledata_loader.add_value("raw_response", raw_response)
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
                f"Error occurred while fetching article details:- {str(exception)}"
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
                self.log("No articles or sitemap url scrapped.")

        except Exception as exception:
            self.log(
                f"Error occurred while exporting file:- {str(exception)} - {reason}"
            )
            raise Exception(
                f"Error occurred while exporting file:- {str(exception)} - {reason}"
            ) from exception
