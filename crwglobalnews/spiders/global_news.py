"""global news spider file"""
import scrapy
from datetime import datetime
from lxml import etree
from crwglobalnews.exceptions import (
    InvalidInputException,
    ParseFunctionFailedException,
    SitemapScrappingException,
    ArticleScrappingException,
    CrawlerClosingException,
    CategoryScrappingException
)
from scrapy.loader import ItemLoader
from crwglobalnews.constant import TODAYS_DATE, LOGGER, LINK_FEED_URL, CATEGORIES_URLS
from abc import ABC, abstractmethod
from crwglobalnews.items import ArticleData
from crwglobalnews.utils import (
    create_log_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)

# create log file
create_log_file()


class BaseSpider(ABC):
    @abstractmethod
    def parse(self, response: scrapy):
        pass

    @abstractmethod
    def parse_link_feed(self, response: scrapy) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: scrapy) -> list:
        pass


class GlobalNewsSpider(scrapy.Spider, BaseSpider):
    """global news spider"""
    name = "global_news"

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """
        A spider to crawl globalnews. ca for news articles. The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.
        ca and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        try:
            super(GlobalNewsSpider, self).__init__(*args, **kwargs)

            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.proxies = kwargs.get('args', {}).get('proxies', None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()

            if self.type == "sitemap":
                if start_date is not None or end_date is not None:
                    LOGGER.info("Date Filter is not available for this website")
                    raise InvalidInputException(
                        "Date Filter is not available for this website"
                    )
                # self.start_urls.append(LINK_FEED_URL)
                for category in CATEGORIES_URLS:
                    self.start_urls.append(category)

            if self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.info("Must have a URL to scrap")
                    raise InvalidInputException("Must have a URL to scrap")

        except Exception as exception:
            LOGGER.info(f"Error occurred in init function in {self.name}:-- {exception}")
            raise InvalidInputException(
                f"Error occurred in init function in {self.name}:-- {exception}"
            )

    def parse(self, response: scrapy, **kwargs):
        """Parses the response object and extracts data based on the type of object.
        Returns:
            generator: A generator that yields scrapy.Request objects to be further parsed by other functions.
        """
        try:
            LOGGER.info("Parse function called on %s", response.url)
            if self.type == "sitemap":
                # yield scrapy.Request(response.url, callback=self.parse_link_feed)
                for category in CATEGORIES_URLS:
                    yield scrapy.Request(category, callback=self.parse_category)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            LOGGER.info(f"Error occurred in parse function: {e}")
            raise ParseFunctionFailedException(
                f"Error occurred in parse function: {e}"
            )

    def parse_link_feed(self, response: scrapy):
        """
        Extracts URLs, titles, and publication dates from a sitemap response and saves them to a list.
        """
        try:
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

                if TODAYS_DATE == published_at:
                    data = {
                        "link": url,
                        "title": title,
                    }
                    self.articles.append(data)

        except Exception as exception:
            LOGGER.info("Error while parsing sitemap: {}".format(exception))
            raise SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_article(self, response: scrapy) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.

        Args:
            response (scrapy.http.Response): The response object containing the article data.

        Returns:
            list: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        try:
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response = get_raw_response(response)
            response_json = get_parsed_json(response)
            response_data = get_parsed_data(response)

            articledata_loader.add_value("raw_response", raw_response)
            articledata_loader.add_value(
                "parsed_json",
                response_json,
            )
            articledata_loader.add_value("parsed_data", response_data)

            self.articles.append(dict(articledata_loader.load_item()))

            return articledata_loader.item

        except Exception as exception:
            LOGGER.info(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def parse_category(self, response: scrapy):         # noqa: C901
        try:
            sub_categories = response.css("#archive-menu li a::attr(href)").getall()
            if len(sub_categories) > 0:
                for category in sub_categories:
                    yield scrapy.Request(category, callback=self.parse_category)

            if response.url in ["https://etcanada.com/"]:
                return
            if ".pdf" in response.url:
                return
            if "/news/" in response.url:
                return
            if "/contests" in response.url:
                return

            links = response.css("div.l-section__main ul.c-posts li a::attr(href)").getall()
            titles = response.css("div.l-section__main ul.c-posts li a span.c-posts__headlineText::text").getall()
            dates = response.css("div.l-section__main ul.c-posts li a div.c-posts__info:nth-child(2)::text").getall()
            today_date_keywords = ["hours", "mins", "hour", "min", "secs", "sec"]

            for link, title, date in zip(links, titles, dates):
                for keyword in today_date_keywords:
                    if keyword.lower() in date:
                        data = {"link": link, "title": title}
                        self.articles.append(data)
                        break

            unique_articles = list(set([tuple(d.items()) for d in self.articles]))
            self.articles = [dict(t) for t in unique_articles]
            return

        except Exception as exception:
            LOGGER.info(
                f"Error occurred while extracting article for link: {response.url}."
                + str(exception)
            )
            raise CategoryScrappingException(
                f"Error occurred while extracting article for link: {str(exception)}"
            )

    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            reason: generated response
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
            ) or (
                stats.get(
                    "downloader/exception_type_count/twisted.internet.error.ConnectionRefusedError",
                    0,
                )
            ):
                self.output_callback("Error in Proxy Configuration")
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                LOGGER.info("No articles or sitemap url scrapped.")
        except Exception as exception:
            LOGGER.info(
                f"Error occurred while closing crawler: {str(exception)} - {reason}"
            )
            raise CrawlerClosingException(
                f"Error occurred while closing crawler: {str(exception)} - {reason}"
            )
