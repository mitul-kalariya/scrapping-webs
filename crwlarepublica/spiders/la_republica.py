import scrapy
import logging
from datetime import datetime
from scrapy.http import XmlResponse
from scrapy.selector import Selector
from crwlarepublica import exceptions
from scrapy.loader import ItemLoader
from crwlarepublica.constant import LOGGER, SITEMAP_URL, TODAYS_DATE
from abc import ABC, abstractmethod
from crwlarepublica.items import ArticleData
from crwlarepublica.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
)


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


class LaRepublicaSpider(scrapy.Spider):
    name = "la_republica"

    def __init__(self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.
        Args:
            type (str): A string indicating the type of data to scrape. Must be either "sitemap" or "article".
            start_date (str): A string representing the start date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            url (str): A string representing the URL of the webpage to be scraped.
            end_date (str): A string representing the end date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            **kwargs: Additional keyword arguments that can be used to pass information to the web scraper.
        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.
        Notes:
            This function initializes a web scraper object and sets various properties based on the arguments passed.
            If the type argument is "sitemap", the start and end dates of the sitemap are validated and set.
            If the type argument is "article",
            the URL to be scraped is validated and set. A log file is created for the web scraper.
        """

        super(LaRepublicaSpider, self).__init__(*args, **kwargs)

        self.output_callback = kwargs.get('args', {}).get('callback', None)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()

        create_log_file()

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
                LOGGER.error("Error while")
                raise exceptions.InvalidInputException("Must have a URL to scrap")

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

        try:
            # breakpoint()
            if self.type == "sitemap":
                if self.start_date and self.end_date:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
                else:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            print(f"Error: {e}")
            self.logger.error(f"{e}")

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
            # breakpoint()
            xmlresponse = XmlResponse(url=response.url, body=response.body, encoding="utf-8")
            xml_selector = Selector(xmlresponse)
            xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            news_namespaces = {"news": "http://www.google.com/schemas/sitemap-news/0.9"}

            # date_lastmod = xml_selector.xpath("//xmlns:lastmod/text()", namespaces=xml_namespaces)
            # for i in date_lastmod.getall():
            #     print(i)
            # ss = xml_selector.xpath("//xmlns:loc/text()", namespaces=xml_namespaces)
            # print("11111111111111111", ss)
            # titles = xml_selector.xpath("//xmlns:title/text()", namespaces=news_namespaces)
            # print("2222222222222222", title)

            # for sitemap in xml_selector.xpath("//xmlns:loc/text()", namespaces=xml_namespaces):
            #     print("11111111111111111", sitemap)
            urls = xml_selector.xpath("//xmlns:loc/text()", namespaces=xml_namespaces).getall()
            titles = xml_selector.xpath("//news:title/text()", namespaces=news_namespaces).getall()
            publication_dates = xml_selector.xpath(
                "//news:publication_date/text()",
                namespaces=news_namespaces
            ).getall()
            # print("@@@@@@@@@@@@@", publication_dates)

            # for url, title in zip(
            #         xml_selector.xpath("//xmlns:loc/text()", namespaces=xml_namespaces).getall(),
            #         xml_selector.xpath("//xmlns:title/text()", namespaces=news_namespaces).getall(),
            # ):
            #     data = {"link": url, "title": title}
            #     self.articles.append(data)

            for url, title, pub_date in zip(urls, titles, publication_dates):
                published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
                # breakpoint()
                if self.start_date and published_at < self.start_date:
                    return
                if self.start_date and published_at > self.end_date:
                    return

                if self.start_date is None and self.end_date is None:
                    if TODAYS_DATE == published_at:
                        data = {
                            "link": url,
                            "title": title,
                        }
                        self.articles.append(data)
                else:
                    if self.start_date and self.end_date:
                        data = {
                            "link": url,
                            "title": title,
                        }
                        self.articles.append(data)

        except Exception as exception:
            self.log(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise exceptions.SitemapScrappingException(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}"
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
            if title := response.css("h1.m-title-single::text").getall():
                data = {"link": response.url, "title": title}
                self.articles.append(data)
        except Exception as exception:
            self.log(
                f"Error occurred while fetching article details from sitemap:- {str(exception)}",
                level=logging.ERROR,
            )
            raise exceptions.SitemapArticleScrappingException(
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
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response = get_raw_response(response)
            articledata_loader.add_value("raw_response", raw_response)

            response_json = get_parsed_json(response)
            articledata_loader.add_value(
                "parsed_json",
                response_json,
            )
            response_data = get_parsed_data(response)
            articledata_loader.add_value("parsed_data", response_data)
            self.articles.append(dict(articledata_loader.load_item()))
            return articledata_loader.item

        except Exception as exception:
            self.log(
                f"Error occurred while scrapping an article for this link {response.url}."
                + str(exception),
                level=logging.ERROR,
            )
            raise exceptions.ArticleScrappingException(
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
