import logging
from datetime import datetime
import json
from abc import ABC, abstractmethod
import scrapy
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from scrapy.exceptions import CloseSpider

from newton_scrapping.items import ArticleData

from ..utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file
)
from newton_scrapping.exceptions import (
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

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class CP24News(scrapy.Spider, BaseSpider):
    name = "cp24"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(
            self, type=None, start_date=None,
            end_date=None, url=None, *args, **kwargs
    ):
        try:
            super(CP24News, self).__init__(*args, **kwargs)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.url = url
            self.error_msg_dict = {}
            self.start_date = start_date  # datetime.strptime(start_date, '%Y-%m-%d')
            self.end_date = end_date  # datetime.strptime(end_date, '%Y-%m-%d')
            self.article_url = url
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
        if self.type == "sitemap":
            try:
                for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                        namespaces=self.namespace).getall()[1:-4]:
                    if "askalawyer" not in site_map_url:
                        yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

            except Exception as exception:
                self.log(
                    f"Error occured while iterating sitemap url. {str(exception)}",
                    level=logging.ERROR,
                )
        elif self.type == "article":
            try:
                yield scrapy.Request(self.url, callback=self.parse_article)
            except Exception as exception:
                self.log(
                    f"Error occured while iterating article url. {str(exception)}",
                    level=logging.ERROR,
                )

    def parse_sitemap(self, response):
        """
        This function parses the sitemap page and extracts the URLs of individual articles.
        :param response: the response object of the sitemap page
        :return: a scrapy.Request object for each individual article URL
        """
        try:

            for article_url in response.css('div.listInnerHorizontal  h2.teaserTitle a::attr("href")').getall():
                
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
            selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()

            try:
                string = json.loads(selector[0])
                published_date = string.get('datePublished')

            except:
                published_date = response.xpath('//meta[@itemprop="datePublished"]/@content').get()

            published_date = datetime.strptime(published_date.split("T")[0], '%Y-%m-%d')
            if self.start_date is None and self.end_date is None:

                if published_date == self.today_date:

                    title = response.css('h1.articleHeadline::text').get()
                    if title:
                        article = {
                            "link": response.url,
                            "title": title,
                        }

                        self.articles.append(article)
                else:
                    self.logger.info("There's no article url and link for Today's Date")

            elif self.start_date <= published_date <= self.end_date:
                title = response.css('h1.articleHeadline::text').get()
                if title:
                    article = {
                        "link": response.url,
                        "title": title,
                    }

                    self.logger.info('Fetching sitemap data for given range')
                    self.articles.append(article)
            else:
                self.logger.info("There's no article url and link for given date of range")

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
            # return self.articles

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
