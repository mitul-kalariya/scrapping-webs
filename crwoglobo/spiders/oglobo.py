"""Spider to scrap HKET news website"""

import logging
from datetime import datetime
from abc import ABC, abstractmethod

import scrapy

from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

from crwoglobo.items import ArticleData
from crwoglobo.constant import SITEMAP_URL, BASE_URL
from crwoglobo.utils import (
    validate,
    get_raw_response,
    get_parsed_json,
    get_parsed_data,
    remove_empty_elements,
)
from crwoglobo.exceptions import (
    SitemapScrappingException,
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
    def parse_sitemap(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class OGloboSpider(scrapy.Spider, BaseSpider):
    """Spider class to scrap sitemap and articles of Sankei News (JP) site"""

    name = "oglobo"
    start_urls = [BASE_URL]
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(OGloboSpider, self).__init__(*args, **kwargs)

        try:
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.proxies = kwargs.get('args', {}).get('proxies', None)
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
                else SITEMAP_URL
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
            for single_date in self.date_range_lst:
                try:
                    day = (
                        single_date.day
                        if len(str(single_date.day)) > 1
                        else f"0{single_date.day}"
                    )
                    month = (
                        single_date.month
                        if len(str(single_date.month)) > 1
                        else f"0{single_date.month}"
                    )
                    year = single_date.year
                    self.logger.debug("Parse function called on %s", response.url)
                    yield scrapy.Request(
                        f"https://oglobo.globo.com/sitemap/oglobo/{year}/{month}/{day}_1.xml",
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
                Selector(response, type="xml").xpath("//sitemap:loc/text()", namespaces=self.namespace).getall()
            ):
                data = {"link": article_url}
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
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                import json
                with open(f"/home/siddharth/scrapy/newton-scrapping/Article/{datetime.strftime(datetime.now(),'%d_%m_%Y')}.json", "+w", encoding="utf-8") as file:
                    json.dump(self.articles, file, indent=4, ensure_ascii = False)
        except Exception as exception:
            self.log(
                f"Error occurred while closing crawler:- {str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise ExportOutputFileException(
                f"Error occurred while closing crawler:- {str(exception)} - {reason}"
            ) from exception
