"""Spider to scrap DD news website"""
import logging
from datetime import datetime, date
from abc import ABC, abstractmethod
import scrapy
from scrapy.loader import ItemLoader
from crwddnews.items import ArticleData
from crwddnews import exceptions
from crwddnews.constant import ARCHIVE_URL, LOGGER
from crwddnews.utils import (
    create_log_file,
    validate_sitemap_date_range,
    get_raw_response,
    get_parsed_data,
    export_data_to_json_file,
)

# create logs
create_log_file()


class BaseSpider(ABC):
    """Abstract Base class for scrapy spider

    Args:
        ABC : Abstract
    """

    # pylint: disable=unnecessary-pass
    @abstractmethod
    def parse(self, response):
        """parse function responsible for calling individual methods for each request"""
        pass

    @abstractmethod
    def parse_archive(self, response: str) -> None:
        """called by parse function when response is sitemap"""
        pass

    def parse_archive_article(self, response: str) -> None:
        """called by parse function when response is sitemap article"""
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        """called by parse function when response is article"""
        pass


class DDNewsSpider(scrapy.Spider, BaseSpider):
    """main spider for parsing sitemap or article"""

    name = "dd_news"

    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        # pylint: disable=redefined-builtin
        """
        Initializes a web scraper object to scrape data from a website or sitemap.
        Args:
            type (str): A string indicating the type of data to scrape.
            Must be either "sitemap" or "article".
            since (str): A string representing the start date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            url (str): A string representing the URL of the webpage to be scraped.
            until (str): A string representing the end date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            **kwargs: Additional keyword arguments
            that can be used to pass information to the web scraper.
        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.
        Notes:
            This function initializes a web scraper object and
            sets various properties based on the arguments passed.
            If the type argument is "sitemap", the start and end dates of
            the sitemap are validated and set.
            If the type argument is "article",
            the URL to be scraped is validated and set. A log file is created for the web scraper.
        """
        try:
            super(DDNewsSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()

            if self.type == "sitemap":
                self.start_urls.append(ARCHIVE_URL)

                self.since = (
                    datetime.strptime(since, "%Y-%m-%d").date() if since else None
                )
                self.until = (
                    datetime.strptime(until, "%Y-%m-%d").date() if until else None
                )

                validate_sitemap_date_range(since, until)

            if self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.info("Must have a URL to scrap")
                    raise exceptions.InvalidInputException("Must have a URL to scrap")

        except Exception as exception:
            LOGGER.info(
                "Error occured in init function in %s:-- %s", self.name, exception
            )
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

    def parse(self, response, **kwargs):
        """
        Parses the given Scrapy response based on the specified type of parsing.
        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.
        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        try:
            if self.type == "sitemap":
                yield scrapy.Request(response.url, callback=self.parse_archive)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as exception:
            LOGGER.info("Error occured in parse function: %s", exception)
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_archive(self, response):
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error while
            parsing the sitemap page.
        """
        try:
            today = date.today().strftime("%m/%d/%Y")
            if self.since and self.until:
                since = self.since.strftime("%m/%d/%Y")
                until = self.until.strftime("%m/%d/%Y")

                if since == until and since == today:
                    url = (
                        "https://ddnews.gov.in/about/news-archive?title=&news_type=All&changed_1="
                        + today
                    )
                elif until == today:
                    url = (
                        "https://ddnews.gov.in/about/news-archive?\
                            title=&news_type=All&changed_1="
                        + since
                    )
                else:
                    url = (
                        "https://ddnews.gov.in/about/news-archive?\
                            title=&news_type=All&changed_1="
                        + since
                        + "&changed_2="
                        + until
                    )
            else:
                url = (
                    "https://ddnews.gov.in/about/news-archive?title=&news_type=All&changed_1="
                    + today
                )
            yield scrapy.Request(url, callback=self.parse_archive_article)
        except BaseException as exception:
            LOGGER.info("Error while parsing sitemap: %s", exception)
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_archive_article(self, response):
        """Extracts article titles and links from the response object and
        yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_archive_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        try:
            links = response.css("span.field-content a::attr(href)").getall()
            titles = response.css("p.archive-title::text").getall()
            for link, title in zip(links, titles):
                if link and title:
                    self.articles.append(
                        {"link": f"https://ddnews.gov.in/{link}", "title": title}
                    )
            pagination = response.css("li.pager-item a::attr(href)").getall()
            for pagination_wise in pagination:
                pagination_url = f"https://ddnews.gov.in{pagination_wise}"
                if len(pagination) >= 1:
                    yield scrapy.Request(
                        pagination_url, callback=self.parse_archive_article
                    )

        except BaseException as exception:
            LOGGER.info("Error while parsing sitemap article: %s", exception)
            raise exceptions.SitemapArticleScrappingException(
                f"Error while parsing sitemap article: {str(exception)}"
            )

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
        try:
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response = get_raw_response(response)
            response_json = {}
            response_data = get_parsed_data(response)
            response_data["time_scraped"] = [str(datetime.now())]

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
                "Error occurred while scrapping an article for this link %s.",
                response.url + str(exception),
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def closed(self, reason: any) -> None:
        """
        Method called when the spider is finished scraping.
        Saves the scraped data to a JSON file with a timestamp
        in the filename.
        """
        try:
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                LOGGER.info("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            LOGGER.info(
                "Error occurred while writing json file %s - %s", str(exception), reason
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while writing json file {str(exception)} - {reason}"
            )
