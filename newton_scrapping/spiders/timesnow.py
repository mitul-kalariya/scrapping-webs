import logging
from datetime import datetime
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


class TimesNow(scrapy.Spider):
    name = "times_now_news"
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(
            self, type=None, start_date=None,
            end_date=None, url=None, *args, **kwargs
    ):
        try:
            super(TimesNow, self).__init__(*args, **kwargs)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.url = url
            self.error_msg_dict = {}
            self.start_date = start_date  # datetime.strptime(start_date, '%Y-%m-%d')
            self.end_date = end_date  # datetime.strptime(end_date, '%Y-%m-%d')
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
                site_map_url = Selector(response, type='xml') \
                    .xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
              
                for url in site_map_url:
                    date = url.split('/')[-1].split('.')[0]

                    _date = datetime.strptime(f"{date}-01", '%Y-%B-%d')
                    if self.today_date:
                        if _date == self.today_date:
                            yield response.follow(url, callback=self.parse_sitemap)
                    else:
                        if self.start_date <= _date <= self.end_date:
                            yield scrapy.Request(
                                url, callback=self.parse_sitemap)
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
           Parses the sitemap and extracts the article URLs and their last modified date.
           If the last modified date is within the specified date range, sends a request to the article URL
           :param response: the response from the sitemap request
           :return: scrapy.Request object
           """
        
        article_urls = Selector(response, type='xml'). \
            xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        mod_date = Selector(response, type='xml') \
            .xpath('//sitemap:lastmod/text()',
                   namespaces=self.namespace).getall()
        try:
            for url, date in zip(article_urls, mod_date):
                _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                if self.today_date:
                    if _date == self.today_date:
                        yield scrapy.Request(
                            url, callback=self.parse_sitemap_article)
                else:
                    if self.start_date <= _date <= self.end_date:
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
        # Extract the article title from the response
        title = response.css('._1FcxJ::text').get()
        # If the title exists, add the article information to the list of articles
        try:
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
