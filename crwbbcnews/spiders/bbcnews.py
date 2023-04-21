import logging
from abc import ABC, abstractmethod
from datetime import datetime

import requests
import scrapy
from scrapy.loader import ItemLoader

from crwbbcnews.constant import TODAYS_DATE, LOGGER, CATEGORY_URL
from crwbbcnews.exceptions import (
    ArticleScrappingException,
    ExportOutputFileException,
    ParseFunctionFailedException,
    CategoryScrappingException,
    InvalidInputException
)
from crwbbcnews.items import ArticleData
from crwbbcnews.utils import (
    create_log_file,
    get_data_from_json,
    get_parsed_json,
    get_raw_response,
    validate_date_range,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Creating an object
logger = logging.getLogger()

BBC_NEWS = "https://www.bbc.com"


class BaseSpider(ABC):
    @abstractmethod
    def parse(self, response):
        pass

    @abstractmethod
    def parse_category(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_category_articles(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class BBCNews(scrapy.Spider, BaseSpider):
    name = "bbc"

    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object with the given parameters.
        Parameters:
        type (str): The type of scraping to be performed. Either "link_feed" or "article".
        sinde (str): The start date of the time period to be scraped, in the format "YYYY-MM-DD".
        url (str): The URL of the article to be scraped. Required if type is "article".
        until (str): The end date of the time period to be scraped, in the format "YYYY-MM-DD".
        **kwargs: Additional keyword arguments to be passed to the superclass constructor.
        Raises:
        ValueError: If the since date and/or until date are invalid.
        InvalidDateRange: If the since is later than the until date.
        Exception: If no URL is provided when type is "article".
        """
        super(BBCNews, self).__init__(*args, **kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.proxies = kwargs.get('args', {}).get('proxies', None)
        self.start_urls = []
        self.articles = []
        self.type = type.lower()
        self.main_json = None
        self.article_url = url

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(CATEGORY_URL)
            self.since = (
                datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
            )
            self.until = (
                datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
            )
            validate_date_range(since, until)
        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.info("Must have a URL to scrap")
                raise InvalidInputException("Must have a URL to scrap")

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
                yield scrapy.Request(response.url, callback=self.parse_category)
            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as exception:
            LOGGER.info(f"Error occured in parse function: {exception}")
            raise ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_category(self, response):  # noqa: C901
        """
        Parses the categories and extracts the article URLs and their last modified date.
        If the last modified date is within the specified date range, sends a request to the article URL
        :param response: the response from the category request
        :return: scrapy.Request object
        """
        try:
            # Extract all category links
            links = response.css(".e11sm0on4 li a::attr(href)").getall()
            for link in links:
                if "co.uk" in link:
                    try:
                        link = link.replace("co.uk", "com")
                        link_response = requests.head(link)
                        link_response.raise_for_status()
                    except Exception:
                        continue
                if "bbc.com" not in link:
                    url = BBC_NEWS + link
                else:
                    url = link
                yield scrapy.Request(url, callback=self.parse_category_articles)
        except BaseException as exception:
            LOGGER.info(f"Error while parsing categories: {str(exception)}")
            raise CategoryScrappingException(
                f"Error while parsing categories: {str(exception)}"
            )

    def parse_category_articles(self, response):
        """Extract artcle links from category pages

        Args:
            response (scrapy.http.Response): The response object containing the HTML of the article page.

        Yields:
            scrapy.Request: A new request object to be sent to the website.
        """
        try:
            todays_date = datetime.today().strftime("%Y-%m-%d")

            articles = response.css(".promo-text")
            if not articles:
                articles = response.css(".e718b9o0")

            article_dates = articles.css("time::attr(datetime)").getall()
            for article in articles:
                published_at = article.css("time::attr(datetime)").get()
                if published_at != todays_date:
                    continue
                link_data = article.css("a::attr(href)").get()
                if "bbc.com" not in link_data:
                    link = BBC_NEWS + link_data
                else:
                    link = link_data
                title = article.css("a::text").get() or article.css("a span::text").get()
                self.articles.append({"link": link, "title": title})

            unique_articles = list(set([tuple(d.items()) for d in self.articles]))
            self.articles = [dict(t) for t in unique_articles]

            page_categories = response.css(".e11sm0on4 li a::attr(href)").getall()
            if 0 < len(page_categories) < 8:
                for link in page_categories:
                    url = BBC_NEWS + link
                    yield scrapy.Request(url, callback=self.parse_category)

            pagination = response.css(".e19602dz5 ul li a::text").getall()
            if len(pagination) > 0:
                for page in range(1, int(pagination[-1]) + 1):
                    pagination_url = str(response.url) + f"?page={page}"
                    if (todays_date in article_dates):
                        yield scrapy.Request(
                            pagination_url, callback=self.parse_category_articles
                        )
        except BaseException as exception:
            LOGGER.info(f"Error while parsing article links from category page: {str(exception)}")
            raise CategoryScrappingException(
                f"Error while parsing article links from category page: {str(exception)}"
            )

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
                parsed_json_dict["imageObjects"] = parsed_json_main
                parsed_json_dict["videoObjects"] = parsed_json_main
                parsed_json_dict["other"] = parsed_json_main

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
                "parsed_data", get_data_from_json(response, parsed_json_data)
            )
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item

        except BaseException as exception:
            LOGGER.info(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:- {str(exception)}"
            )

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
            stats = self.crawler.stats.get_stats()
            if (
                    stats.get(
                        "downloader/exception_type_count/scrapy.core.downloader.handlers.http11.TunnelError",
                        0,
                    )
                    > 0
            ) or (
                    stats.get(
                        "downloader/request_count",
                        0,
                    )
                    == stats.get(
                        "downloader/exception_type_count/twisted.internet.error.TimeoutError",
                        0,
                    )
            ):
                self.output_callback("Error in Proxy Configuration")
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                self.log("No articles or category url scrapped.", level=logging.INFO)
        except BaseException as exception:
            LOGGER.info(
                f"Error occurred while writing json file{str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
