"""Spider to scrap HKET news website"""

import logging
from datetime import datetime
from abc import ABC, abstractmethod

import scrapy

from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

from crwhket.items import ArticleData
from crwhket.constant import LINK_FEED_URL, BASE_URL
from crwhket.utils import (
    validate,
    get_raw_response,
    get_parsed_json,
    get_parsed_data,
    remove_empty_elements,
    get_all_data_from_selenium,
    get_parsed_data_using_selenium,
)
from crwhket.exceptions import (
    SitemapScrappingException,
    SitemapArticleScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
)

# Setting the threshold of logger to DEBUG
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Creating an object
logger = logging.getLogger()


class BaseSpider(ABC):
    @abstractmethod
    def parse(self, response):
        pass

    @abstractmethod
    def parse_link_feed(self, response: str) -> None:
        pass

    def parse_link_feed_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class HKETSpider(scrapy.Spider, BaseSpider):
    """Spider class to scrap sitemap and articles of Sankei News (JP) site"""

    name = "hket"
    start_urls = [BASE_URL]
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    news_namespace = {"sitemap": "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(HKETSpider, self).__init__(*args, **kwargs)

        try:
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.start_urls = []
            self.articles = []
            self.date_range_lst = []
            self.article_url = url
            self.error_msg_dict = {}
            self.type = type
            self.scrape_start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.scrape_end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )

            self.date_range_lst = validate(
                self.type, self.scrape_start_date, self.scrape_end_date, url
            )

            self.start_urls.append(
                url
                if self.type == "article"
                else LINK_FEED_URL
            )

        except Exception as exception:
            self.error_msg_dict["error_msg"] = (
                "Error occurred while taking type, url, since and until args. "
                + str(exception)
            )
            self.log(
                "Error occurred while taking type, url, since and until args. "
                + str(exception),
                level=logging.ERROR,
            )

    def parse(self, response: str, **kwargs) -> None:
        """
        differentiate sitemap and article and redirect its callback to different parser
        Args:
            response: generated response
        Raises:
            CloseSpider: Close spider if error in passed args
            Error if any while scrapping
        Returns:
            None
        """
        if self.error_msg_dict:
            raise CloseSpider(self.error_msg_dict.get("error_msg"))
        if response.status != 200:
            raise CloseSpider(
                f"Unable to scrape due to getting this status code {response.status}"
            )
        self.logger.info("Parse function called on %s", response.url)
        if "sitemap.xml" in response.url:
            self.parse_link_feed(response)
        else:
            yield self.parse_article(response)

    def parse_link_feed(self, response: str) -> None:
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """
        try:
            for url, date, title in zip(
                Selector(response, type="xml").xpath("//sitemap:loc/text()", namespaces=self.namespace).getall(),
                Selector(response, type="xml").xpath(
                    "//sitemap:publication_date/text()",
                    namespaces=self.news_namespace
                ).getall(),
                Selector(response, type="xml").xpath("//sitemap:title/text()", namespaces=self.news_namespace).getall(),
            ):
                date_datetime = datetime.strptime(date.strip()[:10], "%Y-%m-%d")
                if date_datetime.date() in self.date_range_lst:
                    data = {"link": url, "title": title.strip()}
                    self.articles.append(data)
        except Exception as exception:
            self.log(
                "Error occurred while scrapping urls from given sitemap url. "
                + str(exception),
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse_article(self, response: str) -> None:
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
            use_selenium = False
            if "https://invest.hket.com/" in response.url or "https://ps.hket.com/" in response.url:
                use_selenium = True
                data = get_all_data_from_selenium(response.url)
            if use_selenium:
                raw_response_dict = {
                    "content_type": data.get("content-type"),
                    "content": data.get("content"),
                }
                parsed_json_data = data.get("parsed_json")
                parsed_data = get_parsed_data_using_selenium(response, parsed_json_data, data)
            else:
                raw_response_dict = {
                    "content_type": response.headers.get("Content-Type").decode("utf-8"),
                    "content": response.text,
                }
                parsed_json_data = get_parsed_json(response)
                parsed_data = get_parsed_data(response, parsed_json_data)

            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            articledata_loader.add_value("raw_response", raw_response)
            if parsed_json_data:
                articledata_loader.add_value(
                    "parsed_json",
                    parsed_json_data,
                )
            articledata_loader.add_value(
                "parsed_data", parsed_data
            )

            self.articles.append(
                remove_empty_elements(dict(articledata_loader.load_item()))
            )
            return articledata_loader.item

        except Exception as exception:
            self.log(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception),
                level=logging.ERROR,
            )
            raise ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            ) from exception

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
