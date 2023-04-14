import scrapy
from abc import ABC, abstractmethod
from datetime import datetime
from scrapy.loader import ItemLoader
from crwntv import exceptions
from crwntv.constant import LOGGER, SITEMAP_URL, TODAYS_DATE
from crwntv.items import ArticleData
from crwntv.utils import (
    create_log_file,
    export_data_to_json_file,
    get_parsed_data,
    get_parsed_json,
    get_raw_response,
)

# create logger file
create_log_file()


class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class NTvSpider(scrapy.Spider, BaseSpider):
    name = "n_tv"

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """
        Initializes a web scraper object with the given parameters.

        Parameters:
        type (str): The type of scraping to be performed. Either "sitemap" or "article".
        start_date (str): The start date of the time period to be scraped, in the format "YYYY-MM-DD".
        url (str): The URL of the article to be scraped. Required if type is "article".
        end_date (str): The end date of the time period to be scraped, in the format "YYYY-MM-DD".
        **kwargs: Additional keyword arguments to be passed to the superclass constructor.

        Raises:
        ValueError: If the start_date and/or end_date are invalid.
        InvalidDateRange: If the start_date is later than the end_date.
        Exception: If no URL is provided when type is "article".
        """
        try:
            super(NTvSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.articles = []
            self.type = type.lower()
            self.article_url = url

            if self.type == "sitemap":
                if start_date is not None or end_date is not None:
                    LOGGER.info("Date Filter is not available for this website")
                    raise exceptions.InvalidInputException(
                        "Date Filter is not available for this website"
                    )
                self.start_urls.append(SITEMAP_URL)

            elif self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.info("Must have a URL to scrap")
                    raise Exception("Must have a URL to scrap")

        except Exception as exception:
            LOGGER.info(f"Error occured in init function in {self.name}:-- {exception}")
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

    def parse(self, response):
        """
        Parses the response obtained from a website.

        Yields:
        scrapy.Request: A new request object to be sent to the website.

        Raises:
        BaseException: If an error occurs during parsing.
        """
        LOGGER.info("Parse function called on %s", response.url)
        try:
            if self.type == "sitemap":
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as exception:
            LOGGER.info(f"Error occured in parse function: {exception}")
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_sitemap(self, response):  # noqa: C901
        try:
            namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            loc = response.xpath("//xmlns:loc/text()", namespaces=namespaces).getall()
            title = response.xpath(
                "//*[local-name()='title' and namespace-uri()='http://www.google.com/schemas/sitemap-news/0.9']/text()"
            ).getall()
            published_date = response.xpath(
                "//*[local-name()='publication_date' and namespace-uri()='http://www.google.com/schemas/sitemap-news/0.9']/text()"  # noqa: E501
            ).getall()
            for loc, title, pub_date in zip(loc, title, published_date):
                if loc and title and pub_date:
                    published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
                    data = {"link": loc, "title": title}
                    if TODAYS_DATE == published_at:
                        self.articles.append(data)

        except Exception as exception:
            LOGGER.info("Error while parsing sitemap: {}".format(exception))
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_article(self, response):
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
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            LOGGER.info(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
