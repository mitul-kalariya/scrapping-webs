"""Spider to scrap HuffPost news website"""

import logging
from datetime import datetime
from abc import ABC, abstractmethod

import scrapy

from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

from crwhuffpost.items import ArticleData
from crwhuffpost.utils import (
    based_on_scrape_type,
    get_raw_response,
    get_parsed_json,
    export_data_to_json_file,
    get_parsed_data,
    remove_empty_elements,
)
from crwhuffpost.exceptions import (
    SitemapScrappingException,
    SitemapArticleScrappingException,
    ArticleScrappingException,
)
from crwhuffpost.constant import SITEMAP_URL, BASE_URL


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
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class HuffPostSpider(scrapy.Spider, BaseSpider):
    """Spider class to scrape sitemap and article of huffpost website."""

    name = "huff_post"
    start_urls = [BASE_URL]
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(__class__, self).__init__(*args, **kwargs)

        try:
            self.output_callback = kwargs.get("args", {}).get("callback", None)
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

            self.date_range_lst = based_on_scrape_type(
                self.type, self.scrape_start_date, self.scrape_end_date, url
            )
            self.start_urls.append(
                url
                if self.type == "article"
                else SITEMAP_URL
            )

        except Exception as exception:
            self.error_msg_dict["error_msg"] = (
                "Error occurred while taking type, url, start_date and end_date args. "
                + str(exception)
            )
            self.log(
                "Error occurred while taking type, url, start_date and end_date args. "
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

        if "index.xml" in response.url:
            for single_date in self.date_range_lst:
                try:
                    self.logger.debug("Parse function called on %s", response.url)
                    yield scrapy.Request(
                        f"https://www.huffingtonpost.fr/sitemaps/articles/{single_date}.xml",
                        callback=self.parse_sitemap,
                    )
                except Exception as exception:
                    self.log(
                        f"Error occurred while iterating sitemap url. {str(exception)}",
                        level=logging.ERROR,
                    )
        else:
            yield self.parse_article(response)

    def parse_sitemap(self, response: str) -> None:
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
            for article_url in (
                Selector(response, type="xml")
                .xpath("//sitemap:loc/text()", namespaces=self.namespace)
                .getall()
            ):
                yield scrapy.Request(article_url, callback=self.parse_sitemap_article)
        except Exception as exception:
            self.log(
                f"Error occurred while fetching sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapScrappingException(
                f"Error occurred while fetching sitemap:- {str(exception)}"
            ) from exception

    def parse_sitemap_article(self, response: str) -> None:
        """
        parse sitemap article and scrap title and link
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """
        try:
            if title := response.css("h1.article-title::text").get():
                data = {"link": response.url, "title": title}
                self.articles.append(data)
        except Exception as exception:
            self.log(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise SitemapArticleScrappingException(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}"
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
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader = ItemLoader(item=ArticleData(), response=response)

            parsed_json_data = get_parsed_json(response)
            articledata_loader.add_value("raw_response", raw_response)
            if parsed_json_data:
                articledata_loader.add_value(
                    "parsed_json",
                    parsed_json_data,
                )
            articledata_loader.add_value(
                "parsed_data",
                get_parsed_data(
                    response,
                    parsed_json_data.get("main", [{}]),
                    parsed_json_data.get("VideoObject"),
                ),
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

    def closed(self) -> None:
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
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            self.log(
                f"Error occurred while writing json file{str(exception)}",
                level=logging.ERROR,
            )
