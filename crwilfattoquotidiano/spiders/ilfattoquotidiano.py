import logging
from datetime import datetime, date
from abc import ABC, abstractmethod
import scrapy

from scrapy.loader import ItemLoader

from crwilfattoquotidiano import exceptions
from crwilfattoquotidiano.constant import SITEMAP_URL, LOGGER, TODAYS_DATE
from crwilfattoquotidiano.items import ArticleData
from crwilfattoquotidiano.utils import (
    validate_sitemap_date_range,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    export_data_to_json_file,
)


class BaseSpider(ABC):
    """
    Base class for making abstract methods
    """
    # pylint: disable=unnecessary-pass

    @abstractmethod
    def parse(self, response):
        """
        Parses the given Scrapy response based on the specified type of parsing.
        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.
        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        pass

    @abstractmethod
    def parse_archive_categories(self, response: str) -> None:
        """Parses a sitemap page and extracts categories links for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error
            while parsing the sitemap page.
        """
        pass

    def parse_archive(self, response: str) -> None:
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error
            while parsing the sitemap page.
        """
        pass

    def parse_archive_article(self, response: str) -> None:
        """Extracts article titles and links from the response object
        and yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.
        Args:
            response (scrapy.http.Response): The response object containing the article data.
        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        pass


class IlfattoquotidianoSpider(scrapy.Spider, BaseSpider):
    """Spider"""

    name = "ilfattoquotidiano"

    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.
        Args:
            type (str): A string indicating the type of data to scrape. Must be either
            "sitemap" or "article".
            since (str): A string representing the start date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            url (str): A string representing the URL of the webpage to be scraped.
            until (str): A string representing the end date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            **kwargs: Additional keyword arguments that can be used to pass
            information to the web scraper.
        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.
        Notes:
            This function initializes a web scraper object and sets various
            properties based on the arguments passed.
            If the type argument is "sitemap", the start and end dates of
            the sitemap are validated and set.
            If the type argument is "article",
            the URL to be scraped is validated and set. A log file is created for the web scraper.
        """
        try:
            super(IlfattoquotidianoSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.date_range_lst = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()
            self.today = date.today().strftime("%Y-%m-%d")

            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)

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
                "Error occured in init function in %s :-- %s", self.name, exception
            )
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

    def parse(self, response):
        """
        Parses the given Scrapy response based on the specified type of parsing.
        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.
        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        try:
            if self.type == "sitemap":
                yield scrapy.Request(
                    response.url, callback=self.parse_archive_categories
                )

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as exception:
            LOGGER.info("Error occured in parse function: %s", exception)
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_archive_categories(self, response):
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error
            while parsing the sitemap page.
        """

        try:
            links = response.css("div.teaser__text-content a::attr(href)").getall()
            for link in links:
                if link != "https://www.stern.de/noch-fragen/archiv/":
                    yield scrapy.Request(link, callback=self.parse_archive_article)
                else:
                    continue

        except BaseException as exception:
            LOGGER.info("Error while parsing sitemap: %s", exception)
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_archive_article(self, response):
        """Extracts article titles and links from the response object
        and yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        try:
            if self.since and self.until:
                since = str(self.since.month) + str(self.since.year)
                until = str(self.until.month) + str(self.until.year)
                if since == until:
                    date = self.since.strftime("%Y-%m-%d").split("-")
                    link = response.url + f"/?month={date[1]}&year={date[0]}"
                    yield scrapy.Request(
                        link,
                        dont_filter=True,
                        callback=self.parse_archive_article_links,
                    )
                else:
                    since_date = self.since.strftime("%Y-%m-%d").split("-")
                    until_date = self.until.strftime("%Y-%m-%d").split("-")
                    links = [
                        response.url + f"/?month={since_date[1]}&year={since_date[0]}",
                        response.url + f"/?month={until_date[1]}&year={until_date[0]}",
                    ]
                    for link in links:
                        yield scrapy.Request(
                            link,
                            dont_filter=True,
                            callback=self.parse_archive_article_links,
                        )
            else:
                current_date = TODAYS_DATE.strftime("%Y-%m-%d").split("-")
                link = (
                    response.url + f"/?month={current_date[1]}&year={current_date[0]}"
                )
                yield scrapy.Request(
                    link, dont_filter=True, callback=self.parse_archive_article_links
                )
        except Exception as exception:
            LOGGER.info("Error while parsing sitemap article: %s", str(exception))
            raise exceptions.SitemapArticleScrappingException(
            "Error while parsing sitemap article::%s-", str(exception)
            )

    def parse_archive_article_links(self, response):
        """
        gets article links from the archive
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        try:
            links = response.css(
                ".group-teaserlist__item.group-teaserlist__item--teaser-plaintext a::attr(href)"
            ).getall()
            title = response.css(
                ".group-teaserlist__item.group-teaserlist__item--teaser-plaintext h3::text"
            ).getall()
            published_date = response.css(
                ".group-teaserlist__item.group-teaserlist__item--teaser-plaintext time::attr(datetime)"
            ).getall()

            for link, title, pub_date in zip(links, title, published_date):
                publish_date = pub_date.split("T")
                published_at = datetime.strptime(publish_date[0], "%Y-%m-%d").date()
                if self.since and published_at < self.since:
                    continue
                if self.since and published_at > self.until:
                    continue

                if self.since and self.until:
                    data = {"link": link, "title": title}
                    self.articles.append(data)
                elif TODAYS_DATE == published_at:
                    data = {"link": link, "title": title}
                    self.articles.append(data)
                else:
                    continue

            pagination = response.css(
                ".button.u-typo.u-typo--button-text.button--icon.button--icon-arrow-right.button--icon-pos-right"
            ).get()

            if pagination:
                total_pagination = response.css(
                    "li.pagination__page a::attr(href)"
                ).getall()[1:]
                for pagination_wise in total_pagination:
                    pagination_url = pagination_wise
                    if len(pagination) > 1:
                        yield scrapy.Request(
                            pagination_url, callback=self.parse_archive_article_links
                        )

            else:
                pass

        except Exception as exception:
            LOGGER.info("Error while parsing sitemap article: %s", str(exception))
            raise exceptions.SitemapArticleScrappingException(
            "Error while parsing sitemap article:: %s ", str(exception)
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
            response_json = get_parsed_json(response)
            response_data = get_parsed_data(response)
            response_data["source_country"] = ["India"]
            response_data["time_scraped"] = [str(datetime.now())]

            articledata_loader.add_value("raw_response", raw_response)
            articledata_loader.add_value("parsed_json", response_json)
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

        except BaseException as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )