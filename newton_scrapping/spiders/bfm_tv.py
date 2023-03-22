import re
import os
import json
import gzip
import scrapy
import requests
import logging
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    filename="logs.log",
    filemode="a",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()


class InvalidDateRange(Exception):
    """
    This code defines a custom exception class named
        InvalidDateRange which inherits from the Exception class.
    This exception is raised when the date range specified by the user is invalid,
        for example, when the start date is later than the end date.
    """

    pass


class NTvSpider(scrapy.Spider):
    name = "bfm_tv"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
        Initializes a web scraper object with the given parameters.

        Parameters:
        type (str): The type of scraping to be performed. Either "sitemap" or "article".
        start_date (str): The start date of the time period to be scraped, in the format "YYYY-MM-DD".
        url (str): The URL of the article to be scraped. Required if type is "article".
        end_date (str): The end date of the time period to be scraped, in the format "YYYY-MM-DD".
        **kwargs: Additional keyword arguments to be passed to the superclass constructor.

        Raises:
        ValueError: If the start_date and/or end_date are invalid.
        InvalidDateRange: If the start_date is later than the end_date.
        Exception: If no URL is provided when type is "article".
        """
        super().__init__(**kwargs)
        self.start_urls = []
        self.sitemap_data = []
        self.article_json_data = []
        self.type = type.lower()
        self.today_date = datetime.today().strftime("%Y-%m-%d")
        self.today_date = datetime.strptime(self.today_date, "%Y-%m-%d").date()
        self.links_path = "Links"
        self.article_path = "Articles"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        if self.type == "sitemap":
            self.start_urls.append(
                "https://www.bfmtv.com/sitemap_index_arbo_contenu.xml"
            )
            try:
                self.start_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date()
                    if start_date
                    else None
                )
                self.end_date = (
                    datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
                )

                if start_date and not end_date:
                    raise ValueError(
                        "end_date must be specified if start_date is provided"
                    )
                if not start_date and end_date:
                    raise ValueError(
                        "start_date must be specified if end_date is provided"
                    )

                if (
                    self.start_date
                    and self.end_date
                    and self.start_date > self.end_date
                ):
                    raise InvalidDateRange(
                        "start_date should not be later than end_date"
                    )

                if (
                    self.start_date
                    and self.end_date
                    and self.start_date == self.end_date
                ):
                    raise ValueError("start_date and end_date must not be the same")
            except ValueError as e:
                self.logger.error(f"Error in __init__: {e}")
                raise InvalidDateRange("Invalid date format")

    def parse(self, response):
        """
        Parses the response obtained from a website.

        Yields:
        scrapy.Request: A new request object to be sent to the website.

        Raises:
        BaseException: If an error occurs during parsing.
        """
        self.logger.info("Parse function called on %s", response.url)
        try:
            if self.type == "sitemap":
                for sitemap in response.xpath(
                    "//sitemap:loc/text()",
                    namespaces={
                        "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"
                    },
                ):
                    for link in sitemap.getall():
                        r = requests.get(link, stream=True)
                        g = gzip.GzipFile(fileobj=BytesIO(r.content))
                        content = g.read()
                        soup = BeautifulSoup(content, "html.parser")

                        loc = soup.find_all("loc")
                        lastmod = soup.find_all("lastmod")

                        for particular_link, published_date in zip(loc, lastmod):
                            link = particular_link.text
                            published_at = published_date.text
                            date_only = datetime.strptime(
                                published_at[:10], "%Y-%m-%d"
                            ).date()

                            if self.start_date and date_only < self.start_date:
                                continue
                            if self.end_date and date_only > self.end_date:
                                continue

                            if self.start_date is None and self.end_date is None:
                                if date_only != self.today_date:
                                    continue

                            yield scrapy.Request(
                                link,
                                callback=self.make_sitemap,
                                meta={"published_at": published_at},
                            )
        except ValueError as e:
            self.logger.error(f"Error in __init__: {e}")
            raise InvalidDateRange("Invalid date format")

    def make_sitemap(self, response):
        """
        Extracts URLs, titles, and publication dates from a sitemap response and saves them to a list.
        """
        try:
            published_date = response.meta["published_at"][:10]
            date_only = datetime.strptime(published_date, "%Y-%m-%d").date()

            if self.start_date and date_only < self.start_date:
                return
            if self.end_date and date_only > self.end_date:
                return

            link = response.url
            title = response.css("#contain_title::text").get()

            if title:
                data = {
                    "link": link,
                    "title": title,
                }

                if self.start_date is None and self.end_date is None:
                    if date_only == self.today_date:
                        print(
                            "++++++++++++++++++++++++++++++++",
                            date_only,
                            self.today_date,
                        )
                        self.sitemap_data.append(data)
                else:
                    self.sitemap_data.append(data)
        except BaseException as e:
            print(
                f"Error occurring while extracting link, title {e} in make_sitemap function"
            )
            self.logger.error(
                f"Error occurring while extracting link, title {e} in make_sitemap function"
            )

    def closed(self, response):
        """
        Method called when the spider is finished scraping.
        Saves the scraped data to a JSON file with a timestamp
        in the filename.
        """
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        if self.type == "sitemap":
            file_name = f"{self.links_path}/{self.name}-{'sitemap'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.sitemap_data, f, indent=4, default=str)

        if self.type == "article":
            file_name = f"{self.article_path}/{self.name}-{'article'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.article_json_data, f, indent=4)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(NTvSpider)
    process.start()
