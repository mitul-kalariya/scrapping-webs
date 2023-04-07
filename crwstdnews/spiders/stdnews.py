"""Spider to scrap ZEIT news website"""
import re
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime

import scrapy

from crwstdnews.constant import (
    TODAYS_DATE,
    LINK_FEED,
    LOGGER,
)
from crwstdnews import exceptions
from crwstdnews.items import ArticleData
from crwstdnews.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    get_request_headers,
)



class BaseSpider(ABC):
    """Abstract Base class for scrapy spider

    Args:
        ABC : Abstract
    """
    # pylint disable=unnecessary-pass
    @abstractmethod
    def parse(self,response):
        """parse function responsible for calling individual methods for each request"""
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        """called by parse function when response is sitemap"""
        pass

    def parse_sitemap_article(self, response: str) -> None:
        """called by parse function when response is sitemap article"""
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        """called by parse function when response is article"""
        pass


class STDNewsSpider(scrapy.Spider, BaseSpider):
    name = "stdnews"
    start_urls = ["https://std.stheadline.com/realtime/get_more_instant_news"]

    def __init__(self, *args, type=None, url=None, **kwargs):
        # pylint: disable=redefined-builtin
        """
        A spider to crawl globalnews.ca for news articles.
        The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider.
                        Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode.
                              Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode.
                            Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super().__init__(*args, **kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()

        if self.type == "sitemap":
            self.start_urls.append(LINK_FEED)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

        self.request_headers = {
            "authority": "std.stheadline.com",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "dnt": "1",
            "origin": "https://std.stheadline.com",
            "referer": "https://std.stheadline.com/realtime/%E5%8D%B3%E6%99%82",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

    def parse(self, response):
        if self.type
        self.get_sitemap(response)

    def get_sitemap(self, response):
        today_flag = True
        page_counter = 1
        while today_flag == True:
            response_json = (requests.request(
                "POST",
                "https://std.stheadline.com/realtime/get_more_instant_news",
                headers=self.request_headers,
                data="page="+str(page_counter),
            )).json()
            article_list = response_json.get("data")
            for article_data in article_list:
                if "\u65e5\u524d" in article_data.get("publish_datetime"):
                    today_flag = False
                    break
                self.articles.append(
                    {
                        "link":article_data.get("articleLink"),
                        "title":article_data.get("title").get("tc"),
                    }
                )
            page_counter+=1