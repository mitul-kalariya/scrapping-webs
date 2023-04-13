import scrapy
import w3lib.html
from crwardnews.constant import SITEMAP_URL, LOGGER
from crwardnews import exceptions
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from crwardnews.items import ArticleData
from crwardnews.utils import (
    create_log_file,
    validate_sitemap_date_range,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)

# create log file
create_log_file()


class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_archive(self, response: str) -> None:
        pass

    def parse_archive_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class ArdNewsSpider(scrapy.Spider, BaseSpider):
    # Assigning spider name
    name = "ard_news"

    # Initializing the spider class with site_url and category parameters
    def __init__(self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.

        Args:
            type (str): A string indicating the type of data to scrape. Must be either "sitemap" or "article".

            start_date (str): A string representing the start date of
            the sitemap to be scraped. Must be in the format "YYYY-MM-DD".

            url (str): A string representing the URL of the webpage to be scraped.
            end_date (str): A string representing the end date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".

            **kwargs: Additional keyword arguments that can be used to pass information to the web scraper.

        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.

        Notes:
            This function initializes a web scraper object and sets various properties based on the arguments passed to
            it. If the type argument is "sitemap", the start and end dates of the sitemap are validated and set.
            If the type argument is "article", the URL to be scraped is validated and set.
            A log file is created for the web scraper.

        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.

        Notes:
        This function initializes a web scraper object and sets various properties based on the arguments passed to it.
        If the type argument is "sitemap",
            the start and end dates of the sitemap are validated and set.
        If the type argument is "article", the URL to be scraped is validated and set.
            A log file is created for the web scraper.
        """
        try:
            super(ArdNewsSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get('args', {}).get('callback', None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.sitemap_json = {}
            self.type = type.lower()
            self.date_wise = []

            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)
                self.start_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
                )
                self.end_date = (
                    datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
                )
                validate_sitemap_date_range(start_date, end_date)

            if self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.info("Must have a URL to scrap")
                    raise exceptions.InvalidInputException("Must have a URL to scrap")

        except Exception as exception:
            LOGGER.info(f"Error occured in init function in {self.name}:-- {exception}")
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
            LOGGER.info("Parse function called on %s", response.url)
            if self.type == "sitemap":
                yield scrapy.Request(response.url, callback=self.parse_archive)

            elif self.type == "article":
                yield self.parse_article(response)

        except BaseException as exception:
            LOGGER.info(f"Error occured in parse function: {exception}")
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
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
            response_data["source_country"] = ["Germany"]
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
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def parse_archive(self, response):
        """Parses a sitemap page and extracts links and titles for further processing.

        Args:
            response (scrapy.http.Response): The HTTP response object containing the sitemap page.

        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.

        Raises:
            exceptions.SitemapScrappingException: If there is an error while parsing the sitemap page.

        """
        try:

            # Get the start and end dates as datetime objects
            start_date = (
                datetime.strptime(str(self.start_date), "%Y-%m-%d")
                if self.start_date
                else None
            )
            end_date = (
                datetime.strptime(str(self.end_date), "%Y-%m-%d")
                if self.end_date
                else None
            )

            # Create a list of dates within the range
            date_wise = []
            if start_date and end_date:
                while start_date <= end_date:
                    date_wise.append(start_date.date())
                    start_date += timedelta(days=1)

            if self.start_date is None and self.end_date is None:
                for link in response.css("a"):
                    url = link.css("::attr(href)").get()
                    title = link.css(".teaser-xs__headline , .hyphenate").get()
                    published_at = link.css(".teaser-xs__date::text").get()

                    if url and title and published_at:
                        title = w3lib.html.remove_tags(title)
                        data = {
                            "link": url,
                            "title": title.replace("\n", "").strip(),
                        }

                        self.articles.append(data)
            elif self.start_date and self.end_date:
                for i in date_wise:
                    date_wise_url = f"https://www.tagesschau.de/archiv/?datum={i}"
                    yield scrapy.Request(
                        date_wise_url, callback=self.parse_archive_article
                    )
        except BaseException as exception:
            LOGGER.info(f"Error while parsing sitemap: {exception}")
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_archive_article(self, response):
        """Extracts article titles and links from the response object and yields a Scrapy request for each article.

        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.

        Yields:
            A Scrapy request for each article URL in the sitemap,
                with the `parse_archive_datewise` method as the callback and the article link and title as metadata.

        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        try:
            for link in response.css("a"):
                url = link.css("::attr(href)").get()
                title = link.css(".teaser-xs__headline, .hyphenate").get()
                published_at = link.css(".teaser-xs__date::text").get()

                if url and title and published_at:
                    title = w3lib.html.remove_tags(title)
                    data = {
                        "link": url,
                        "title": title.replace("\n", "").strip(),
                    }

                    self.articles.append(data)
            pagination = response.css(".paginierung__liste li a::attr(href)").getall()
            for pagination_wise in pagination:
                pagination_url = "https://www.tagesschau.de/archiv/" + pagination_wise
                if len(pagination) > 1:
                    yield scrapy.Request(
                        pagination_url, callback=self.parse_archive_article
                    )

        except BaseException as exception:
            LOGGER.info(f"Error while parsing sitemap article: {exception}")
            raise exceptions.SitemapArticleScrappingException(
                f"Error while parsing sitemap article: {str(exception)}"
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
                LOGGER.info("No articles or sitemap url scrapped.")

        except Exception as exception:
            LOGGER.info(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
