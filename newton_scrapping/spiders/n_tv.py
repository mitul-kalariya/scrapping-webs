import gzip
import scrapy
import requests
import logging
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from newton_scrapping.constants import BASE_URL, SITEMAP_URL, LOGGER
from newton_scrapping import exceptions
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
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


class NTvSpider(scrapy.Spider, BaseSpider):
    name = "n_tv"

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
        self.articles = []
        self.type = type.lower()
        self.article_url = url

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(SITEMAP_URL)
            self.start_urls.append(BASE_URL)
            self.start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )
            validate_sitemap_date_range(start_date, end_date)
        elif self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                self.logger.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

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
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            print(f"Error occurring while parsing sitemap {e} in parse function")
            self.logger.error(
                f"Error occurring while parsing sitemap {e} in parse function"
            )

    def parse_sitemap(self, response):
        try:
            for sitemap in response.xpath(
                "//sitemap:loc/text()",
                namespaces={"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"},
            ):
                for link in sitemap.getall():
                    r = requests.get(link, stream=True)
                    g = gzip.GzipFile(fileobj=BytesIO(r.content))
                    content = g.read()
                    soup = BeautifulSoup(content, "html.parser")

                    loc = soup.find_all("loc")
                    lastmod = soup.find_all("lastmod")

                    for particular_link, published_date in zip(loc, lastmod):
                        if "thema" in particular_link:
                            continue
                        link = particular_link.text
                        published_at = published_date.text
                        date_only = datetime.strptime(
                            published_at[:10], "%Y-%m-%d"
                        ).date()

                        if self.start_date and date_only < self.start_date:
                            continue
                        if self.end_date and date_only > self.end_date:
                            continue

                        yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            meta={"published_at": published_at},
                        )
        except BaseException as e:
            LOGGER.error(f"Error while parsing sitemap: {e}")
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):
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
            title = response.css(".article__headline::text").get()

            data = {
                "link": link,
                "title": title,
            }

            if self.start_date is None and self.end_date is None:
                today_date = datetime.today().strftime("%Y-%m-%d")
                today_date = datetime.strptime(today_date, "%Y-%m-%d").date()
                if date_only == today_date:
                    print("++++++++++++++++++++++++++++++++", date_only, today_date)
                    self.articles.append(data)
            else:
                print("------------------------------------------------")
                self.articles.append(data)
        except BaseException as e:
            print(
                f"Error occurring while extracting link, title {e} in make_sitemap function"
            )
            self.logger.error(
                f"Error occurring while extracting link, title {e} in make_sitemap function"
            )

    def parse_article(self, response):
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
        response_data["country"] = ["Germany"]
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
    process.crawl(NTvSpider)
    process.start()
