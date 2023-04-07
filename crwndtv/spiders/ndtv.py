import logging
from datetime import datetime
from abc import ABC, abstractmethod
import scrapy


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


class NDTVSpider(scrapy.Spider, BaseSpider):
    """Spider"""

    name = "ndtv"
