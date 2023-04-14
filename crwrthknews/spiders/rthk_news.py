"""Spider to scrap CBC news website"""

import scrapy
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from scrapy.exceptions import CloseSpider
from scrapy.loader import ItemLoader
from crwrthknews.constant import BASE_URL, ARCHIVE_URL
from crwrthknews.items import ArticleData

from crwrthknews.utils import (
    based_on_scrape_type,
    date_in_date_range,
    get_raw_response,
    get_parsed_json,
    get_article_json,
    create_log_file,
)
from crwrthknews.exceptions import (
    SitemapScrappingException,
    ArticleScrappingException,
    ExportOutputFileException,
)

# create log file
create_log_file()

# Creating an object
logger = logging.getLogger()


class BaseSpider(ABC):
    @abstractmethod
    def parse(self, response):
        pass

    @abstractmethod
    def parse_archive(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class RthkNewsSpider(scrapy.Spider, BaseSpider):
    """Spider class to scrap sitemap and articles of CBC News site"""

    name = "rthk_news"
    start_urls = [
        BASE_URL,
    ]

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
            self.start_urls.append(url if self.type == "article" else ARCHIVE_URL)
        except Exception as exception:
            self.error_msg_dict["error_msg"] = (
                "Error occurred while taking type, url, start_date and end_date args. "
                + str(exception)
            )
            self.log(
                "Error occurred while taking type, url, start_date and end_date args. "
                + str(exception),
                level=logging.INFO,
            )

    def parse(self, response: str, **kwargs) -> None:
        """differentiate sitemap and article and redirect its callback to different parser
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
        if "news-archive" in response.url:
            for single_date in self.date_range_lst:
                try:
                    self.logger.info("Parse function called on %s", response.url)

                    yield scrapy.Request(
                        "https://news.rthk.hk/rthk/ch/"
                        + f"news-archive.htm?archive_year={single_date.year}"
                        + f"&archive_month={single_date.month}"
                        + f"&archive_day={single_date.day}&archive_cat=all",
                        callback=self.parse_archive,
                    )
                except Exception as exception:
                    self.log(
                        f"Error occurred while iterating sitemap url. {str(exception)}",
                        level=logging.INFO,
                    )
        else:
            yield self.parse_article(response)

    def parse_archive(self, response: str) -> None:
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """

        for url, title, date in zip(
            response.css(
                "div.newsContainer div.item div span.title a::attr(href)"
            ).getall(),
            response.css(
                "div.newsContainer div.item div span.title a::attr(title)"
            ).getall(),
            response.css(
                "div.newsContainer div.item div span.newsArchiveLiveTime::text"
            ).getall(),
        ):
            try:
                date_datetime = datetime.strptime(date[:-10].strip(), "%Y-%m-%d")
                url = BASE_URL.replace("/rthk/ch/", "") + url
                if date_in_date_range(date_datetime, self.date_range_lst):
                    data = {"link": url.split("?")[0], "title": title}
                    self.articles.append(data)
            except Exception as exception:
                self.log(
                    f"Error occurred while fetching sitemap:- {str(exception)}",
                    level=logging.INFO,
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
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response_dict = {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            }
            raw_response = get_raw_response(response, raw_response_dict)
            articledata_loader.add_value("raw_response", raw_response)

            parsed_json_data = get_parsed_json(response)
            articledata_loader.add_value("parsed_json", parsed_json_data)
            data = get_article_json(response)
            articledata_loader.add_value("parsed_data", data)
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item

        except Exception as exception:
            self.log(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception),
                level=logging.INFO,
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
                f"Error occurred while exporting file:- {str(exception)} - {reason}",
                level=logging.INFO,
            )
            raise ExportOutputFileException(
                f"Error occurred while exporting file:- {str(exception)} - {reason}"
            ) from exception
