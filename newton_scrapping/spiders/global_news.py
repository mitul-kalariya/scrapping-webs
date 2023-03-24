import scrapy
import logging
from datetime import datetime
from lxml import etree
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from newton_scrapping import exceptions
from scrapy.loader import ItemLoader
from newton_scrapping.constant import TODAYS_DATE, LOGGER
from abc import ABC, abstractmethod
from newton_scrapping.items import ArticleData
from newton_scrapping.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)


class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class GlobalNewsSpider(scrapy.Spider, BaseSpider):
    name = "global_news"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
        A spider to crawl globalnews.ca for news articles. The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super().__init__(**kwargs)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append("https://globalnews.ca/news-sitemap.xml")
            self.start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )
            validate_sitemap_date_range(start_date, end_date)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

    def parse(self, response):
        """Parses the response object and extracts data based on the type of object.
        Returns:
            generator: A generator that yields scrapy.Request objects to be further parsed by other functions.
        """
        if self.type == "sitemap":
            if self.start_date and self.end_date:
                LOGGER.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_sitemap)
            else:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

        elif self.type == "article":
            article_data = self.parse_article(response)
            yield article_data
            

    def parse_sitemap(self, response):
        """
        Extracts URLs, titles, and publication dates from a sitemap response and saves them to a list.
        """
        root = etree.fromstring(response.body)
        urls = root.xpath(
            "//xmlns:loc/text()",
            namespaces={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
        )
        titles = root.xpath(
            "//news:title/text()",
            namespaces={"news": "http://www.google.com/schemas/sitemap-news/0.9"},
        )
        publication_dates = root.xpath(
            "//news:publication_date/text()",
            namespaces={"news": "http://www.google.com/schemas/sitemap-news/0.9"},
        )

        for url, title, pub_date in zip(urls, titles, publication_dates):
            published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
            if self.start_date and published_at < self.start_date:
                return
            if self.start_date and published_at > self.end_date:
                return

            if self.start_date is None and self.end_date is None:
                if TODAYS_DATE == published_at:
                    data = {
                        "url": url,
                        "title": title,
                    }
                    self.articles.append(data)
            else:
                data = {
                    "url": url,
                    "title": title,
                }
                self.articles.append(data)


    def parse_sitemap_article(self, response):
        pass

    def parse_article(self, response) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.

        Args:
            response (scrapy.http.Response): The response object containing the article data.

        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        articledata_loader = ItemLoader(item=ArticleData(), response=response)
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        response_data["source_country"] = ["Canada"]
        response_data["time_scraped"] = [str(datetime.now())]

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        self.articles.append(dict(articledata_loader.load_item()))
        return articledata_loader.item


    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            response: generated response
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
            exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while writing json file{str(exception)} - {reason}",
                level=logging.ERROR,
            )


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(GlobalNewsSpider)
    process.start()
