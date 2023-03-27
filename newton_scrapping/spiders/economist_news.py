import os
import pdb
from abc import ABC, abstractmethod
import logging
import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector

from newton_scrapping.itemLoader import ArticleDataLoader
from newton_scrapping.items import ArticleData
from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from newton_scrapping.exceptions import (
    SitemapScrappingException,
    SitemapArticleScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
)
from newton_scrapping.utils import (
    check_cmd_args,
    get_parsed_data,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    filename="leparisien.log",
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


class Economist(scrapy.Spider, BaseSpider):
    name = "economist_canada"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        try:
            super(Economist, self).__init__(*args, **kwargs)
            self.start_urls = []
            self.articles = []
            self.type = type
            self.error_msg_dict = {}
            self.url = url
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
        if response.status != 200:
            raise CloseSpider(
                f"Unable to scrape due to getting this status code {response.status}"
            )
        if self.type == "sitemap":
            try:
                for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                         namespaces=self.namespace).getall()[4:]:
                    yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
            except Exception as exception:
                self.log(
                    f"Error occurred while iterating sitemap url. {str(exception)}",
                    level=logging.ERROR,
                )
        if self.type == "article":
            try:
                yield scrapy.Request(self.url, callback=self.parse_article)
            except Exception as exception:
                self.log(
                    f"Error occurred while parsing article url. {str(exception)}",
                    level=logging.ERROR,
                )

    def parse_sitemap(self, response):
        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        sitemap_articel_urls = []
        mod_date = Selector(response, type='xml').xpath('//sitemap:lastmod/text()', namespaces=self.namespace).getall()
        try:
            if self.today_date:
                for url, date in zip(article_urls, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if _date == self.today_date:
                        yield scrapy.Request(url, callback=self.parse_sitemap_article)
            else:
                for url, date in zip(article_urls, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if self.start_date <= _date <= self.end_date:
                        sitemap_articel_urls.append(url)
                yield from response.follow_all(sitemap_articel_urls, callback=self.parse_sitemap_article)
        except Exception as exception:
            self.log(
                f"Error occurred while fetching sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse_sitemap_article(self, response):
        try:
            title = response.css('#content h1::text').get()
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
        try:
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader = ArticleDataLoader(item=ArticleData())
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

            parsed_json_data = get_parsed_json(parsed_json_dict)
            articledata_loader.add_value("raw_response", raw_response)
            if parsed_json_data:
                articledata_loader.add_value(
                    "parsed_json",
                    parsed_json_data,
                )
            exit()
            articledata_loader.add_value(
                "parsed_data", get_parsed_data(self, response, parsed_json_data)
            )
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item
        except Exception as exception:
            self.logger.exception(
                f"Error occurred while fetching article details:- {str(exception)}"
            )
            self.log(
                f"Error occurred while fetching article details:- {str(exception)}",
                level=logging.ERROR,
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            ) from exception

        # headline = response.css('#content h1::text').get()
        # alternative_headline = response.css('#content h2::text').get()
        #
        # selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        # logo_height = response.css('#ds-economist-logo::attr("height")').get()
        # logo_width = response.css('#ds-economist-logo::attr("width")').get()
        #
        # json_data = json.loads(selector[0])
        #
        # article = {
        #     'raw_response': {
        #         "content_type": response.headers.get("Content-Type").decode("utf-8"),
        #         "content": response.text,
        #     },
        #     "parsed_json": {
        #         "main": {
        #             "@context": json_data['@context'],
        #             "@type": json_data['@type'],
        #             "mainEntityOfPage": {
        #                 "@type": "WebPage",
        #                 "@id": json_data['mainEntityOfPage']
        #             },
        #             "headline": json_data['headline'],
        #             "alternativeHeadline": alternative_headline,
        #             "dateModified": json_data['dateModified'],
        #             "datePublished": json_data['datePublished'],
        #             "description": json_data['description'],
        #             "author": {"@type": json_data['author']['@type'], "name": json_data['author']['name'],
        #                        "url": json_data['author']['logo']['url']},
        #             "publisher": {'@type': json_data['publisher']['@type'],
        #                           'name': json_data['publisher']['name'],
        #                           'logo': {'@type': json_data['publisher']['logo']['@type'],
        #                                    'url': json_data['publisher']['logo']['url'],
        #                                    'width': {'@type': "Distance",
        #                                              "name": f"{logo_width} Px"},
        #                                    'height': {'@type': "Distance",
        #                                               'name': f"{logo_height} Px"}}},
        #             "image": {
        #                 "@type": "ImageObject",
        #                 "url": json_data['image'],
        #             }
        #
        #         },
        #         "misc": json_data
        #     },
        #     "parsed_data": {
        #         "author": [{"@type": json_data['author']['@type'], "name": json_data['author']['name'],
        #                     "url": json_data['author']['logo']['url']}],
        #         "description": [json_data['description']],
        #         "modified_at": [json_data['dateModified']],
        #         "published_at": [json_data['datePublished']],
        #         "publisher": [{'@type': json_data['publisher']['@type'],
        #                        'name': json_data['publisher']['name'],
        #                        'logo': {'@type': json_data['publisher']['logo']['@type'],
        #                                 'url': json_data['publisher']['logo']['url'],
        #                                 'width': {'@type': "Distance",
        #                                           "name": f"{logo_width} Px"},
        #                                 'height': {'@type': "Distance",
        #                                            'name': f"{logo_height} Px"}}}],
        #         "text": [json_data['articleBody']],
        #         "thumbnail_image": [json_data["thumbnailUrl"]],  # need to look it
        #         "title": [headline],
        #         "images": [{"link": json_data['image']}],
        #         "section": [json_data['articleSection']],
        #         "tags": json_data['keywords']
        #     }
        # }
        # self.articles.append(article)

    def closed(self, reason):
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
