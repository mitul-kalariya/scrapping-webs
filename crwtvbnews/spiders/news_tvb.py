import logging
import scrapy
from datetime import datetime
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from crwtvbnews.items import ArticleData

from crwtvbnews.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
)

from crwtvbnews.exceptions import (
    ArticleScrappingException,
    ExportOutputFileException,
)


class NewsTVB(scrapy.Spider):
    name = "tvb"
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(NewsTVB, self).__init__(*args, **kwargs)
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
        If `type` is "sitemap", extracts sitemap URLs from the XML content of the response and sends a
        request for each of them to Scrapy's engine with the callback function `parse_sitemap`.
        If `type` is "articles", sends a request for the given URL to Scrapy's engine with the callback functio
        n `parse_article`.
        This function is intended to be used as a Scrapy spider callback function.
        :param response: A Scrapy HTTP response object containing sitemap or article content.
        :return: A generator of Scrapy Request objects, one for each sitemap or article URL found in the response.
        """
        if self.type == "sitemap":
            article_url = Selector(response, type='xml')\
                .xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
            article_title = Selector(response, type='xml')\
                .xpath('//news:title/text()', namespaces=self.namespace).getall()
            publication_date = Selector(response, type='xml')\
                .xpath('//news:publication_date/text()', namespaces=self.namespace).getall()
            for url, title, date in zip(article_url, article_title, publication_date):
                _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                if self.today_date:
                    if _date == self.today_date:
                        article = {
                            "link": url,
                            "title": title
                        }
                        self.articles.append(article)
                else:
                    if self.start_date <= _date <= self.end_date:
                        article = {
                            "link": url,
                            "title": title
                        }
                        self.articles.append(article)
        elif self.type == "article":
            yield self.parse_article(response)

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

        except Exception as exception:
            self.log(
                f"Error occurred while closing crawler:- {str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while closing crawler:- {str(exception)} - {reason}"
            ) from exception
