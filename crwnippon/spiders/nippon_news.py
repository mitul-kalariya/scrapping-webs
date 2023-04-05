import logging
from abc import ABC, abstractmethod
from datetime import datetime

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import XmlResponse
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings

from crwnippon import exceptions
from crwnippon.constant import LOGGER, SITEMAP_URL, TODAYS_DATE
from crwnippon.items import ArticleData
from crwnippon.utils import (
    create_log_file,
    get_parsed_data,
    get_parsed_json,
    get_raw_response,
    validate_sitemap_date_range,
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


class NipponNews(scrapy.Spider, BaseSpider):
    # Assigning spider name
    name = "nippon_news"

    # Initializing the spider class with site_url and category parameters
    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.

        Args:
            type (str): A string indicating the type of data to scrape. Must be either "sitemap" or "article".

            since (str): A string representing the start date of
            the sitemap to be scraped. Must be in the format "YYYY-MM-DD".

            url (str): A string representing the URL of the webpage to be scraped.
            until (str): A string representing the end date of the sitemap to be scraped.
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
        super(NipponNews, self).__init__(*args, **kwargs)
        self.output_callback = kwargs.get("args", {}).get("callback", None)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(SITEMAP_URL)
            self.since = (
                datetime.strptime(since, "%Y-%m-%d").date() if since else TODAYS_DATE
            )
            self.until = (
                datetime.strptime(until, "%Y-%m-%d").date() if until else TODAYS_DATE
            )
            validate_sitemap_date_range(since, until)
        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise exceptions.InvalidInputException("Must have a URL to scrap")

    def parse(self, response):
        """
        Parses the response obtained from a website.
        Yields:
        scrapy.Request: A new request object to be sent to the website.
        Raises:
        BaseException: If an error occurs during parsing.
        """
        self.logger.info("Parse function called on %s", response.url)
        try:
            if self.type == "sitemap":
                if self.since and self.until:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
                else:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)

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
            response_data["source_country"] = ["Japan"]
            response_data["time_scraped"] = [str(datetime.now())]

            articledata_loader.add_value("raw_response", raw_response)
            articledata_loader.add_value(
                "parsed_json",
                response_json,
            )
            articledata_loader.add_value("parsed_data", response_data)
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item
        except BaseException as exception:
            LOGGER.info(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception)
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:- {str(exception)}"
            )

    def parse_sitemap(self, response):
        """
        Function to parse a sitemap response by date
        Returns:
            Yields scrapy.Request objects for each link found in the sitemap.
        Description:
        This function takes in a scrapy response object and parses it by date to extract the sitemap links.
        For each sitemap link found, it yields a scrapy.Request object to the parse_sitemap function.
        """
        try:
            # Create an XmlResponse object from the response
            xmlresponse = XmlResponse(
                url=response.url, body=response.body, encoding="utf-8"
            )
            # Create a Selector object from the XmlResponse
            xml_selector = Selector(xmlresponse)
            # Define the XML namespaces used in the sitemap
            xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            # Loop through each sitemap URL in the XML response
            links = xml_selector.xpath(
                "//xmlns:loc/text()", namespaces=xml_namespaces
            ).getall()
            published_date = xml_selector.xpath(
                "///xmlns:lastmod/text()", namespaces=xml_namespaces
            ).getall()

            for link, pub_date in zip(links, published_date):
                if link and pub_date:
                    published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()

                    if self.since and published_at < self.since:
                        return

                    if self.since and published_at > self.until:
                        return

                    if self.since is None and self.until is None:
                        if TODAYS_DATE == published_at:
                            yield scrapy.Request(
                                link,
                                callback=self.parse_sitemap_article,
                                meta={"link": link, "pub_date": published_at},
                            )
                    else:
                        if self.since and self.until:
                            yield scrapy.Request(
                                link,
                                callback=self.parse_sitemap_article,
                                meta={"link": link, "pub_date": published_at},
                            )
        except BaseException as exception:
            LOGGER.error(f"Error while parsing sitemap: {str(exception)}")
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_sitemap_article(self, response):
        """
        Extracts URLs, titles, and publication dates from a sitemap response and saves them to a list.
        """
        try:
            url = response.meta["link"]
            title = response.css(".c-h1::text").get()

            data = {
                "link": url,
                "title": title,
            }
            self.articles.append(data)

        except exceptions.SitemapScrappingException as exception:
            LOGGER.error(f"Error while parsing sitemap article: {str(exception)}")
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
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
        except Exception as exception:
            LOGGER.error(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )
            raise exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(NipponNews)
    process.start()
