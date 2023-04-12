import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

import scrapy
from scrapy.loader import ItemLoader
from scrapy.selector import Selector

from crwcp24.exceptions import (
    ArticleScrappingException,
    ExportOutputFileException,
    SitemapArticleScrappingException,
    SitemapScrappingException,
)
from crwcp24.items import ArticleData
from crwcp24.utils import (
    check_cmd_args,
    get_parsed_data,
    get_parsed_json,
    get_raw_response,
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


class CP24News(scrapy.Spider, BaseSpider):
    name = "cp24"

    namespace = {
        "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
    }

    def __init__(
        self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs
    ):
        try:
            super(CP24News, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.url = url
            self.error_msg_dict = {}
            self.start_date = start_date
            self.end_date = end_date
            self.article_url = url
            self.today_date = None
            check_cmd_args(self, self.start_date, self.end_date)

        except Exception as exception:
            self.error_msg_dict["error_msg"] = (
                "Error occurred while taking type, url, start_date and end_date args. "
                + str(exception)
            )
            self.log(
                "Error occurred while taking type, url, start_date and end_date args. "
                + str(exception),
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while iterating sitemap url:- {str(exception)}"
            ) from exception

    def parse(self, response):
        """
        Parses the given `response` object and extracts sitemap URLs or sends a
        request for articles based on the `type` attribute of the class instance.
        If `type` is "sitemap", extracts sitemap URLs from the XML content of the
        response and sends a request for each of them to Scrapy's engine with the
        callback function `parse_sitemap`.
        If `type` is "articles", sends a request for the given URL to Scrapy's engine
        with the callback function `parse_article`.
        This function is intended to be used as a Scrapy spider callback function.
        :param response: A Scrapy HTTP response object containing sitemap or article content.
        :return: A generator of Scrapy Request objects, one for each sitemap
        or article URL found in the response.
        """
        try:
            if self.type == "sitemap":
                for site_map_url in (
                    Selector(response, type="xml")
                    .xpath("//sitemap:loc/text()", namespaces=self.namespace)
                    .getall()[1:-4]
                ):
                    if "askalawyer" not in site_map_url:
                        yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

            elif self.type == "article":
                yield self.parse_article(response)
        except Exception as exception:
            self.log(
                f"Error occured while iterating {self.type} url. {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while iterating {self.type} url:- {str(exception)}"
            ) from exception

    def parse_sitemap(self, response):
        """
        This function parses the sitemap page and extracts the URLs of individual articles.
        :param response: the response object of the sitemap page
        :return: a scrapy.Request object for each individual article URL
        """
        try:

            for article_url in response.css(
                'div.listInnerHorizontal  h2.teaserTitle a::attr("href")'
            ).getall():

                yield scrapy.Request(article_url, callback=self.parse_sitemap_article)

        except Exception as exception:
            self.log(
                f"Error occurred while fetching article url:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching article url:- {str(exception)}"
            ) from exception

    def parse_sitemap_article(self, response):
        """
        This function parses the sitemap page and extracts the URLs of individual articles.

        :param response: the response object of the sitemap page
        :type response: scrapy.http.Response

        :return: a scrapy.Request object for each individual article URL
        :rtype: scrapy.Request
        """
        try:
            selector = response.xpath(
                '//script[@type="application/ld+json"]/text()'
            ).getall()

            try:
                string = json.loads(selector[0])
                published_date = string.get("datePublished")

            except:  # noqa: E722
                published_date = response.xpath(
                    '//meta[@itemprop="datePublished"]/@content'
                ).get()

            published_date = datetime.strptime(published_date.split("T")[0], "%Y-%m-%d")
            if self.start_date is None and self.end_date is None:

                if published_date == self.today_date:

                    title = response.css("h1.articleHeadline::text").get()
                    if title:
                        article = {
                            "link": response.url,
                            "title": title,
                        }

                        self.articles.append(article)
                else:
                    self.logger.info("There's no article url and link for Today's Date")

            elif self.start_date <= published_date <= self.end_date:
                title = response.css("h1.articleHeadline::text").get()
                if title:
                    article = {
                        "link": response.url,
                        "title": title,
                    }

                    self.logger.info("Fetching sitemap data for given range")
                    self.articles.append(article)
            else:
                self.logger.info(
                    "There's no article url and link for given date of range"
                )

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
                parsed_json_dict["ImageGallery"] = parsed_json_main
                parsed_json_dict["videoObjects"] = parsed_json_main
                parsed_json_dict["imageObjects"] = parsed_json_main
                parsed_json_dict["other"] = parsed_json_main

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
