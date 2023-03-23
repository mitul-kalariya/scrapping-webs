"""Spider to scrap Globe and Mail online (EN) news website"""

import os
import json
import logging
from datetime import datetime
from abc import ABC, abstractmethod

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings

from newton_scrapping.exceptions import InvalidInputException, ArticleScrappingException, \
    SitemapArticleScrappingException, SitemapScrappingException, ExportOutputFileException
from newton_scrapping.utils import validate, get_date_range, get_raw_response, get_parsed_json, get_parsed_data

# Setting the threshold of logger to DEBUG
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
        # parse_sitemap_article will be called from here
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class TheGlobeAndMailSpider(scrapy.Spider, BaseSpider):
    """Spider class to scrap sitemap and articles of Globe and Mail online (EN) site"""

    name = "the_globe_and_mail"
    start_urls = ["http://www.theglobeandmail.com/"]
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(
            self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(TheGlobeAndMailSpider, self).__init__(*args, **kwargs)

        self.start_urls = []
        self.articles = []
        self.date_range_lst = []
        self.error_msg_dict = {}
        self.article_url = url
        self.scrape_start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        self.scrape_end_date = (
            datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        )
        self.type = type

        self.error_msg_dict = validate(type, url, self.scrape_start_date, self.scrape_end_date)
        if self.error_msg_dict:
            raise InvalidInputException(self.error_msg_dict.get("error_msg"))

        if self.type == "sitemap":
            self.start_urls.append(
                "https://www.theglobeandmail.com/web-sitemap.xml"
            )
            self.date_range_lst = get_date_range(self.scrape_start_date, self.scrape_end_date)
        elif self.type == "article":
            self.start_urls.append("https://www.theglobeandmail.com/")

    def parse(self, response):
        """
        differentiate sitemap and article and redirect its callback to different parser
        """

        self.logger.info("Parse function called on %s", response.url)
        if "web-sitemap.xml" in response.url:
            yield scrapy.Request(response.url, callback=self.parse_sitemap)
        else:
            yield scrapy.Request(self.article_url, callback=self.parse_article)

    def parse_sitemap(self, response):
        """
        parse sitemap and scrap urls
        """

        for url, date in zip(
            Selector(response, type="xml").xpath("//sitemap:loc/text()", namespaces=self.namespace).getall(),
            Selector(response, type="xml").xpath("//sitemap:lastmod/text()", namespaces=self.namespace).getall(),
        ):
            try:
                date_datetime = datetime.strptime(date.strip()[:10], "%Y-%m-%d")
                if date_datetime.date() in self.date_range_lst:
                    yield scrapy.Request(
                        url.strip(), callback=self.parse_sitemap_article
                    )
            except SitemapScrappingException as exception:
                self.log(
                    "Error occurred while scrapping urls from given sitemap url. "
                    + str(exception),
                    level=logging.ERROR,
                )
                raise SitemapScrappingException(str(exception))

    def parse_sitemap_article(self, response):
        """
        parse sitemap article and  scrap title and link
        """
        try:
            title = response.css("h1.c-primary-title::text").get()
            if title:
                article = {"link": response.url, "title": title}
                self.articles.append(article)
        except SitemapArticleScrappingException as exception:
            self.log(
                "Error occurred while scraping sitemap's article. " + str(exception),
                level=logging.ERROR,
            )
            raise SitemapArticleScrappingException(str(exception))

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        """
        try:
            article = {
                "raw_response": get_raw_response(response),
                "parsed_json": get_parsed_json(response),
                "parsed_data": get_parsed_data(response),
            }
            self.articles.append(article)

            return self.articles

        except ArticleScrappingException as exception:
            self.log(
                "Error occurred while scrapping an article for this link {response.url}."
                + str(exception),
                level=logging.ERROR,
            )
            raise ArticleScrappingException(str(exception))

    def closed(self, response):
        """
        store all scrapped data into json file with given date in filename
        """
        try:
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                folder_structure = ""
                if self.type == "sitemap":
                    folder_structure = "Links"
                    filename = f'{self.name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
                elif self.type == "article":
                    folder_structure = "Article"
                    filename = f'{self.name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
                if not os.path.exists(folder_structure):
                    os.makedirs(folder_structure)
                with open(f"{folder_structure}/{filename}.json", "w") as file:
                    json.dump(self.articles, file, indent=4)
        except ExportOutputFileException as exception:
            self.log(
                "Error occurred while writing json file" + str(exception),
                level=logging.ERROR,
            )
            raise ExportOutputFileException(str(exception))


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(TheGlobeAndMailSpider, type="sitemap")
    process.start()
