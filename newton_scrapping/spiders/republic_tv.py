import os
import json
import scrapy
from dateutil import parser
from datetime import datetime
from scrapy.loader import ItemLoader
from newton_scrapping.items import ArticleData
from newton_scrapping.utils import (
    parse_sitemap_main,
    get_parsed_data,
    get_parsed_json,
    get_raw_response,
)

class RepublicTvSpider(scrapy.Spider):
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
        self.start_urls = []
        self.sitemap_data = []
        self.articles = []
        self.type = type.lower()
        # self.start_date = start_date
        # self.end_date = end_date
        self.today_date = datetime.today().strftime("%Y-%m-%d")
        self.links_path = "Links"
        self.article_path = "Article"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        self.start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )

        self.end_date = (
            datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        )

        if self.type == "sitemap":
            parse_sitemap_main(self, self.start_urls, start_date, end_date)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                self.logger.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

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
                    yield scrapy.Request(response.url, callback=self.parse_by_date)
                else:
                    self.logger.info("Parse function called on %s", response.url)
                    yield scrapy.Request(response.url, callback=self.parse_by_date)
            elif self.type == "article":
               self.parse_article(response)


        except BaseException as e:
            print(f"Error: {e}")
            self.logger.error(f"{e}")


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
        articledata_loader = ItemLoader(item=ArticleData(), response=response)
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        response_data["country"] = ["India"]
        response_data["time_scraped"] = [str(datetime.now())]

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        self.articles.append(dict(articledata_loader.load_item()))
        return articledata_loader.item


    def parse_by_date(self, response):
        """
        Parses a webpage response object and yields scrapy requests for each sitemap XML link found.

        Yields:
        scrapy.Request: A scrapy request object for each sitemap XML link found in the response.
        """
        self.logger.info("Parse by date at %s", response.url)
        if "sitemap.xml" in response.url:
            for sitemap in response.xpath(
                "//sitemap:loc/text()",
                namespaces={"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"},
            ):
                if sitemap.get().endswith(".xml"):
                    for link in sitemap.getall():
                        if self.start_date is None and self.end_date is None:
                            if self.today_date.replace("-", "") in link:
                                yield scrapy.Request(link, callback=self.parse_sitemap)
                        else:
                            yield scrapy.Request(link, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
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
        namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        links = response.xpath("//n:url/n:loc/text()", namespaces=namespaces).getall()
        published_at = response.xpath('//*[local-name()="lastmod"]/text()').get()
        published_date = parser.parse(published_at).date() if published_at else None
        for link in links:
            yield scrapy.Request(
                link,
                callback=self.parse_sitemap_link_title,
                meta={"link": link, "published_date": published_date},
            )

    def parse_sitemap_link_title(self, response):
        """
        Parses the link, title, and published date from a sitemap page.

        Notes:
        - Adds the parsed data to the scraper's sitemap_data list.
        - Skips the link if the published date is outside the scraper's specified date range.
        """
        link = response.meta["link"]
        published_date = response.meta["published_date"]
        title = response.css(".story-title::text").get().strip()

        if self.start_date and published_date < self.start_date:
            return
        if self.end_date and published_date > self.end_date:
            return

        data = {"link": link, "title": title}

        self.sitemap_data.append(data)

    def closed(self, response):
        """
        Method called when the spider is finished scraping.
        Saves the scraped data to a JSON file with a timestamp
        in the filename.
        """
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        if self.type == "sitemap":
            file_name = f"{self.links_path}/{self.name}-{'sitemap'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.sitemap_data, f, indent=4, default=str)

        if self.type == "article":
            file_name = f"{self.article_path}/{self.name}-{'article'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.articles, f, indent=4)