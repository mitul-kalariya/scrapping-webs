import logging
import scrapy
import w3lib.html
from datetime import datetime,timedelta,date
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from crwddnews.items import ArticleData
from crwddnews import exceptions
from crwddnews.constant import SITEMAP_URL, LOGGER
from crwddnews.utils import (create_log_file, validate_sitemap_date_range, get_raw_response, get_parsed_data,
                              get_parsed_json, export_data_to_json_file, )



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


class DDNewsSpider(scrapy.Spider, BaseSpider):
    name = "dd_news"
    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.
        Args:
            type (str): A string indicating the type of data to scrape. Must be either "sitemap" or "article".
            since (str): A string representing the start date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            url (str): A string representing the URL of the webpage to be scraped.
            until (str): A string representing the end date of the sitemap to be scraped.
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
        try:
            super(DDNewsSpider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()

            if self.type == "sitemap":
                print("------------------------------")
                self.start_urls.append(SITEMAP_URL)

                self.since = (datetime.strptime(since, "%Y-%m-%d").date() if since else None)
                self.until = (datetime.strptime(until, "%Y-%m-%d").date() if until else None)

                validate_sitemap_date_range(since, until)
                print("+++++++++++++++++++++++++++")

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
            if self.type == "sitemap":
                if self.since and self.until:
                    print("=============================")
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)
                else:
                    yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as e:
            LOGGER.info(f"Error occured in parse function: {e}")
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {e}"
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



    def parse_sitemap(self, response):
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
            since = (
                datetime.strptime(str(self.since), "%Y-%m-%d")
                if self.since
                else None
            )
            until = (
                datetime.strptime(str(self.until), "%Y-%m-%d")
                if self.until
                else None
            )
            print(since)
            print(until)
            if since and until:
                url = f"https://ddnews.gov.in/about/news-archive?title=&news_type=All&changed_1="

            # current_date = date.today().isoformat()   
            # days_before = (date.today()-timedelta(days=30)).isoformat()
            # print(current_date)
            # print(days_before)
            # Create a list of dates within the range
            
        except BaseException as e:
            LOGGER.info(f"Error while parsing sitemap: {e}")
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(e)}"
            )

    def parse_sitemap_article(self, response):
        """Extracts article titles and links from the response object and yields a Scrapy request for each article.
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
                        pagination_url, callback=self.parse_sitemap_article
                    )
        except BaseException as e:
            LOGGER.info(f"Error while parsing sitemap article: {e}")
            raise exceptions.SitemapArticleScrappingException(
                f"Error while parsing sitemap article: {str(e)}"
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
            # else:
            #     export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            exceptions.ExportOutputFileException(f"Error occurred while writing json file{str(exception)} - {reason}")
            LOGGER.info(f"Error occurred while writing json file{str(exception)} - {reason}")