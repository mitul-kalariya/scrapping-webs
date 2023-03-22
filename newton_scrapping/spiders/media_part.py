import re
import os
import json
import scrapy
import requests
import logging
from datetime import datetime
from io import BytesIO
from PIL import Image
from scrapy.http import XmlResponse
from scrapy.selector import Selector
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Setting the threshold of logger to DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    filename="logs.log",
    filemode="a",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Creating an object
logger = logging.getLogger()

class InvalidDateRange(Exception):
    """
    This code defines a custom exception class named
    InvalidDateRange which inherits from the Exception class.
    This exception is raised when the date range specified by the user is invalid,
    for example, when the start date is later than the end date.
    """

    pass


class MediaPartSpider(scrapy.Spider):
    name = "media_part"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
        A spider to crawl mediapart.fr for news articles.
        The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of mediapart.fr
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super().__init__(**kwargs)
        self.start_urls = []
        self.sitemap_data = []
        self.article_json_data = []
        self.type = type.lower()
        self.today_date = datetime.today().strftime("%Y-%m-%d")
        self.links_path = "Links"
        self.article_path = "Article"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        if self.type == "sitemap":
            self.start_urls.append("https://www.mediapart.fr/sitemap_index.xml")
            try:
                self.start_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date()
                    if start_date
                    else None
                )
                self.end_date = (
                    datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
                )
                if start_date and not end_date:
                    raise ValueError(
                        "end_date must be specified if start_date is provided"
                    )
                if not start_date and end_date:
                    raise ValueError(
                        "start_date must be specified if end_date is provided"
                    )
                if (
                    self.start_date
                    and self.end_date
                    and self.start_date > self.end_date
                ):
                    raise InvalidDateRange(
                        "start_date should not be later than end_date"
                    )
                if (
                    self.start_date
                    and self.end_date
                    and self.start_date == self.end_date
                ):
                    raise ValueError("start_date and end_date must not be the same")
            except ValueError as e:
                self.logger.error(f"Error in __init__: {e}", exc_info=True)
                raise InvalidDateRange(e)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                self.logger.error("Error while")
                raise Exception("Must have a URL to scrap")

    def parse(self, response):
        """
        Parse the response and extract data based on the spider's type and configuration.

        Yields:
            If the spider's type is "sitemap" and a start and
                end date are specified, a request is yielded to parse by date.
            If the spider's type is "article", a dictionary of parsed data is appended to the article_json_data list.

        Raises:
            BaseException: If an error occurs during parsing, an error is logged and printed to the console.
        """
        try:
            self.logger.info("Parse function called on %s", response.url)
            if self.type == "sitemap":
                if self.start_date and self.end_date:
                    yield scrapy.Request(response.url, callback=self.parse_by_date)
                else:
                    yield scrapy.Request(response.url, callback=self.parse_by_date)

            if self.type == "article":
                response_json = self.response_json(response)
                response_data = self.response_data(response)
                data = {
                    "raw_response": {
                        "content_type": "text/html; charset=utf-8",
                        "content": response.css("html").get(),
                    },
                }
                if response_json:
                    data["parsed_json"] = response_json
                if response_data:
                    response_data["country"] = ["France"]
                    response_data["time_scraped"] = [str(datetime.now())]
                    data["parsed_data"] = response_data

                self.article_json_data.append(data)
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def parse_by_date(self, response):

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
            for sitemap in xml_selector.xpath(
                "//xmlns:loc/text()", namespaces=xml_namespaces
            ):
                # Loop through each link in the sitemap and create a scrapy request for it
                for link in sitemap.getall():
                    yield scrapy.Request(link, callback=self.parse_sitemap)
        # If there's any error during the above process, log it and print
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def parse_sitemap(self, response):

        """
        This function takes in a response object and parses the sitemap.
        It extracts the links and published dates from the response object
        and uses them to make requests to other pages.

        Yields:
            scrapy.Request: A request object with the link and published date as metadata.
            The request object is sent to the 'parse_sitemap_link_title' callback function for further processing.
        """
        try:
            # Define the namespace for the sitemap
            namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Extract the links and published dates from the sitemap
            links = response.xpath("//n:loc/text()", namespaces=namespaces).getall()
            published_date = response.xpath(
                '//*[local-name()="lastmod"]/text()'
            ).getall()

            # Loop through the links and published dates
            for link, pub_date in zip(links, published_date):
                # Convert the published date to a datetime object
                published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()

                # Convert today's date to a datetime object
                today_date = datetime.strptime(self.today_date, "%Y-%m-%d").date()

                # If the published date falls within the specified date range, make a request to the link
                if (
                    self.start_date
                    and self.end_date
                    and self.start_date <= published_at <= self.end_date
                ):
                    yield scrapy.Request(
                        link,
                        callback=self.parse_sitemap_link_title,
                        meta={"link": link, "published_date": published_at},
                    )

                # If the published date is today's date, make a request to the link
                elif today_date == published_at:
                    yield scrapy.Request(
                        link,
                        callback=self.parse_sitemap_link_title,
                        meta={"link": link, "published_date": published_at},
                    )
                else:
                    continue
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def parse_sitemap_link_title(self, response):
        try:
            link = response.meta["link"]
            published_date = response.meta["published_date"]
            title = response.css("h1#page-title::text").get()
            if self.start_date and published_date < self.start_date:
                return
            if self.start_date and published_date > self.end_date:
                return
            data = {
                "link": link,
                "title": title,
            }
            if title:
                self.sitemap_data.append(data)
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def response_json(self, response):
        """
        Extracts relevant information from a news article web page using the given
        Scrapy response object and the URL of the page.

        Args:
        - response: A Scrapy response object representing the web page to extract
          information from.
        - current_url: A string representing the URL of the web page.

        Returns:
        - A dictionary representing the extracted information from the web page.
        """
        try:

            parsed_json = {}
            main = self.get_main(response)
            if main:
                parsed_json["main"] = main

            misc = self.get_misc(response)
            if misc:
                parsed_json["misc"] = misc

            return parsed_json

        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def response_data(self, response):
        """
        Extracts data from a news article webpage and returns it in a dictionary format.

        Parameters:
        response (scrapy.http.Response): A scrapy response object of the news article webpage.

        Returns:
        dict: A dictionary containing the extracted data from the webpage, including:
             - 'publisher': (str) The name of the publisher of the article.
             - 'article_catagory': The region of the news that the article refers to
             - 'headline': (str) The headline of the article.
             - 'authors': (list) The list of authors of the article, if available.
             - 'published_on': (str) The date and time the article was published.
             - 'updated_on': (str) The date and time the article was last updated, if available.
             - 'text': (list) The list of text paragraphs in the article.
             - 'images': (list) The list of image URLs in the article, if available. (using bs4)

        """
        try:
            main_dict = {}
            pattern = r"[\r\n\t\"]+"
            publisher = self.extract_publisher(response)
            if publisher:
                main_dict["publisher"] = publisher

            headline = response.css("h1.l-article__title::text").getall()
            if headline:
                main_dict["title"] = headline

            authors = self.extract_author(response)
            if authors:
                main_dict["author"] = authors

            published_on = response.css("div.splitter__first").get()
            if published_on:
                published_on = (
                    re.sub(pattern, "", published_on.split(">")[-3]).strip("</p")
                ).strip()
                main_dict["published_at"] = [published_on]

            description = response.css("p.news__heading__top__intro::text").get()
            if description:
                main_dict["description"] = [description]

            article_text = response.css("p.dropcap-wrapper::text").getall()
            if article_text:
                main_dict["text"] = [" ".join(article_text).replace("\n", "")]

            article_lang = response.css("html::attr(lang)").get()
            if article_lang:
                main_dict["language"] = [article_lang]

            return main_dict

        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def get_main(self, response):
        """
        returns a list of main data available in the article from application/ld+json
        Parameters:
            response:
        Returns:
            main data
        """
        try:
            data = []
            misc = response.css('script[type="application/ld+json"]::text').getall()
            for block in misc:
                data.append(json.loads(block))
            return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error while getting main: {e}")

    def get_misc(self, response):
        """
        returns a list of misc data available in the article from application/json
        Parameters:
            response:
        Returns:
            misc data
        """
        try:
            data = []
            misc = response.css('script[type="application/json"]::text').getall()
            for block in misc:
                data.append(json.loads(block))
            return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error while getting misc: {e}")

    def extract_publisher(self, response) -> list:
        """
        Extracts publisher information from the given response object and returns it as a dictionary.

        Returns:
        - A dictionary containing information about the publisher.The dictionary has the following keys:
        ---
        @id: The unique identifier for the publisher.
        @type: The type of publisher (in this case, always "NewsMediaOrganization").
        name: The name of the publisher.
        logo: Logo of the publisher as an image object
        """
        try:
            logo = response.css('head link[rel="icon"]::attr(href)').get()
            img_response = requests.get(logo)
            width, height = Image.open(BytesIO(img_response.content)).size
            a_dict = {
                "@id": "mediapart.fr",
                "@type": "NewsMediaOrganization",
                "name": "Global NEWS",
                "logo": {
                    "@type": "ImageObject",
                    "url": logo,
                    "width": {"@type": "Distance", "name": str(width) + " px"},
                    "height": {"@type": "Distance", "name": str(height) + " px"},
                },
            }
            return [a_dict]
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def extract_author(self, response) -> list:
        """
        The extract_author function extracts information about the author(s)
        of an article from the given response object and returns it in the form of a list of dictionaries.

        Parameters:
            response (scrapy.http.Response): The response object containing the HTML of the article page.

        Returns:
            A list of dictionaries, where each dictionary contains information about one author.

        """
        try:
            info = response.css("div.splitter__first p a")
            pattern = r"[\r\n\t\"]+"
            data = []
            if info:
                for i in info:
                    temp_dict = {}
                    temp_dict["@type"] = "Person"
                    name = i.css("a::text").get()
                    if name:
                        name = re.sub(pattern, "", name).strip()
                        temp_dict["name"] = "".join((name.split("("))[0::-2])
                        url = i.css("a::attr(href)").get()
                        if url:
                            temp_dict["url"] = "https://www.mediapart.fr" + url
                        data.append(temp_dict)
                return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def closed(self, response):
        """
        Saves the sitemap data or article JSON data to a file with a timestamped filename.
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
                json.dump(self.article_json_data, f, indent=4, default=str)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(MediaPartSpider)
    process.start()
