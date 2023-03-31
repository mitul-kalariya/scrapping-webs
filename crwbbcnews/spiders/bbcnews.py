import logging
from datetime import datetime
from abc import ABC, abstractmethod
import scrapy
from scrapy.loader import ItemLoader

from crwbbcnews.items import ArticleData
from crwbbcnews.utils import (
    check_cmd_args,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file,
    get_data_from_json
)
from crwbbcnews.exceptions import ExportOutputFileException, SitemapArticleScrappingException, ArticleScrappingException
from crwbbcnews.constant import BASE_URL


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


class BBCNews(scrapy.Spider, BaseSpider):
    """
    BBCNews spider
    """
    name = "bbc"
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(
        self, type=None, start_date=None,
        end_date=None, url=None, *args, **kwargs
                ):
        super(BBCNews, self).__init__(*args, **kwargs)
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
            try:
                groups = response.json()['content']['groups']

                for group in groups:
                    group_types = group['items']
                    for group_type in group_types:
                        article_timestamp = group_type['timestamp']
                        article_date = datetime.fromtimestamp(article_timestamp/1000).date()

                        if self.start_date and self.end_date:
                            if self.start_date.date() <= article_date <= self.end_date.date():
                                url = BASE_URL + group_type['locators']['assetUri']
                                article = {
                                    "link": url,
                                    "title": group_type['headlines']['headline']
                                }
                                self.articles.append(article)

                        elif self.today_date.date() == article_date:
                            url = BASE_URL + group_type['locators']['assetUri'] + '.json'
                            article = {
                                "link": url,
                                "title": group_type['headlines']['headline']
                            }
                            self.articles.append(article)

            except Exception as e:
                self.logger.exception(f"Error in parse_json :- {e}")

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
        pass

    def parse_sitemap_article(self, response):
        """
           Parse article information from a given sitemap URL.
           :param response: HTTP response from the sitemap URL.
           :return: None
        """
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
            articledata_loader = ItemLoader(item=ArticleData(), response=response.json())
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
            articledata_loader.add_value("parsed_json", dict())
            articledata_loader.add_value(
                "parsed_data", get_data_from_json(response.json())
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
