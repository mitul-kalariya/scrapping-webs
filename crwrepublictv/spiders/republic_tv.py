import scrapy
import logging
from dateutil import parser
from datetime import datetime
from crwrepublictv.constant import SITEMAP_URL, TODAYS_DATE, LOGGER, PAGINATION
from crwrepublictv import exceptions
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from crwrepublictv.items import ArticleData
from crwrepublictv.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)


class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass


class RepublicTvSpider(scrapy.Spider, BaseSpider):
    name = "republic_tv"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
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
        super().__init__(**kwargs)
        self.output_callback = kwargs.get('args', {}).get('callback', None)
        self.start_urls = []
        self.articles = []
        self.articles_url = url
        self.type = type.lower()
        self.article_url = url

        self.ignored_url = [
            "https://bharat.republicworld.com/",
            "https://bharat.republicworld.com/shows",
            "https://bharat.republicworld.com/technology-news",
            "https://bharat.republicworld.com/sports-news",
            "https://bharat.republicworld.com/india-news",
            "https://bharat.republicworld.com/lifestyle",
            "https://bharat.republicworld.com/entertainment-news",
            "https://bharat.republicworld.com/world-news",
        ]
        self.pagination = []

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(SITEMAP_URL)
            self.start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else TODAYS_DATE
            )
            self.end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else TODAYS_DATE
            )

            validate_sitemap_date_range(start_date, end_date)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Error while")
                raise exceptions.InvalidInputException("Must have a URL to scrap")

    def parse(self, response):
        """
        Parses the response obtained from a website.

        Yields:
        scrapy.Request: A new request object to be sent to the website.

        Raises:
        BaseException: If an error occurs during parsing.
        """
        try:
            self.logger.info("Parse function called on %s", response.url)
            if self.type == "sitemap":
                if self.start_date and self.end_date:
                    self.logger.info("Parse function called on %s", response.url)
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
                else:
                    self.logger.info("Parse function called on %s", response.url)
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            print(f"Error while parse function: {e}")
            self.logger.error(f"Error while parse function: {e}")

    def parse_sitemap(self, response):
        """
        Parses a webpage response object and yields scrapy requests for each sitemap XML link found.

        Yields:
        scrapy.Request: A scrapy request object for each sitemap XML link found in the response.
        """
        try:
            response.selector.remove_namespaces()
            links = response.xpath("//url/loc/text()").getall()
            for link in links:
                if link in self.ignored_url or "shows" in link:
                    continue
                else:
                    yield scrapy.Request(link, callback=self.parse_sitemap_article)
        except BaseException as e:
            LOGGER.error("Error while parsing sitemap: {}".format(e))
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):
        """
        Parses a sitemap and sends requests to scrape each of the links.

        Yields:
        scrapy.Request: A request to scrape each of the links in the sitemap.

        Notes:
        The sitemap must be in the XML format specified by the sitemaps.org protocol.
        The function extracts the links from the sitemap
            and sends a request to scrape each link using the `parse_sitemap_link_title` callback method.
        The function also extracts the publication date of the sitemap, if available, and
            passes it along as a meta parameter in each request.
        """
        try:
            pagi = response.css(
                ".page-jump-number~ .page-jump+ .page-jump div a::attr(href)"
            ).get()
            # last_num = int(pagi.split("/")[-1])
            self.start_urls.append(response.request.url)
            for i in range(1, PAGINATION):
                yield scrapy.Request(
                    response.request.url + "/" + str(i),
                    callback=self.parse_sitemap_by_title_link,
                    meta={"index": i},
                )
        except BaseException as e:
            exceptions.SitemapArticleScrappingException(
                f"Error while parse sitemap article: {e}"
            )
            LOGGER.error(f"Error while parse sitemap article: {e}")

    def parse_sitemap_by_title_link(self, response):
        """
        Parses the link, title, and published date from a sitemap page.

        Notes:
        - Adds the parsed data to the scraper's sitemap_data list.
        - Skips the link if the published date is outside the scraper's specified date range.
        """
        try:
            for link in response.css("div#republic-dom a"):
                url = link.css("::attr(href)").get()
                title = link.css(
                    ".font18::text , .font16::text , .lineHeight31px::text"
                ).get()
                if url and title:
                    yield scrapy.Request(
                        url,
                        callback=self.parse_sitemap_datewise,
                        meta={"url": url, "title": title},
                    )
        except BaseException as e:
            exceptions.SitemapArticleScrappingException(
                f"Error while parse sitemap article: {e}"
            )
            LOGGER.error(f"Error while parse sitemap article: {e}")

    def parse_sitemap_datewise(self, response):
        url = response.meta["url"]
        title = response.meta["title"]
        published_at = response.css(".time-elapsed time::attr(datetime)").get()[:10]
        published_at = datetime.strptime(published_at, "%Y-%m-%d").date()
        today = datetime.today().strftime("%Y-%m-%d")
        today = datetime.strptime(today, "%Y-%m-%d").date()

        if self.start_date and published_at < self.start_date:
            return
        if self.start_date and published_at > self.end_date:
            return
        data = {
            "link": url,
            "title": title,
        }

        if url and title and published_at:
            if self.start_date is None and self.end_date is None:
                if today == published_at:
                    self.articles.append(data)
            else:
                if self.start_date and self.end_date:
                    self.articles.append(data)

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
        articledata_loader = ItemLoader(item=ArticleData(), response=response)
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        response_data["source_country"] = ["India"]
        response_data["time_scraped"] = [str(datetime.now())]

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        self.articles.append(dict(articledata_loader.load_item()))
        return articledata_loader.item

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
        except Exception as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while writing json file{str(exception)} - {reason}",
                level=logging.ERROR,
            )
