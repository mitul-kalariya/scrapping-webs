import scrapy
import requests
from datetime import datetime
from crwyohapnews.constant import LINK_FEED_URL, LOGGER, TODAYS_DATE, BASE_URL
from crwyohapnews import exceptions
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from crwyohapnews.items import ArticleData
from crwyohapnews.utils import (
    create_log_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    export_data_to_json_file,
)

# create log file
create_log_file()


class BaseSpider(ABC):
    """Abstract Base class for scrapy spider
    Args:
        ABC : Abstract
    """

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
    def parse_link_feed(self, response: str) -> None:
        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.
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


class YohapNewsSpider(scrapy.Spider):
    name = "yohapnews"
    start_urls = [BASE_URL]

    def __init__(self, *args, type=None, url=None, **kwargs):
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
            super().__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()
            self.proxies = kwargs.get("args", {}).get("proxies", None)
            

            if self.type == "sitemap":
                self.start_urls.append(BASE_URL)
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
                yield scrapy.Request(response.url, callback=self.parse_link_feed)

            elif self.type == "article":
                yield self.parse_article(response)

        except BaseException as exception:
            LOGGER.info(f"Error occured in parse function: {exception}")
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_link_feed(self, response):
        today = TODAYS_DATE.strftime("%Y%m%d")
        ct_counter = 1
        api_response = True
        # for ct_counter there are 1- 8or9 possible values
        while api_response is True:
            # getting the api response for given ct_counter
            params = {"ct": ct_counter, "srt": "l", "d": today}
            response_json = requests.get(
                LINK_FEED_URL,
                params=params,
            )
            if response_json:
                # if we get response we search for all the number of pages
                page_count = (response_json.json()).get("totalPage")
                page_block = 1
                while page_block <= page_count:
                    # setting value of p as per the counter of the page in given page count index
                    params["p"] = page_block
                    page_response_json = requests.get(
                        LINK_FEED_URL, params=params
                    ).json()
                    # from each page index getting the article data list
                    article_list = page_response_json.get("list")
                    for article_data in article_list:
                        # fetching the published date for each block in article_list
                        article_date = datetime.fromtimestamp(
                            int(article_data.get("createdAt")) / 1000
                        ).date()

                        # if the article_date is
                        if article_date < TODAYS_DATE:
                            page_block = page_count
                            break
                        self.articles.append(
                            {
                                "link": BASE_URL
                                + "news/"
                                + article_data.get("sequence"),
                                "title": article_data.get("title"),
                            }
                        )
                    page_block += 1

                # updating the counter after searching pages of current ct_counter
                ct_counter += 1
            else:
                api_response = False
                break

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
        try:
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response = get_raw_response(response)
            response_json = get_parsed_json(response)
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
                "Error occurred while scrapping an article for this link %s %s",
                response.url,
                str(exception),
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
