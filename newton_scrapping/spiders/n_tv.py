import re
import os
import json
import gzip
import scrapy
import requests
import logging
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    filename="logs.log",
    filemode="a",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()


class InvalidDateRange(Exception):
    """
    This code defines a custom exception class named
    InvalidDateRange which inherits from the Exception class.
    This exception is raised when the date range specified by the user is invalid,
    for example, when the start date is later than the end date.
    """

    pass


class NTvSpider(scrapy.Spider):
    name = "n_tv"

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
        self.article_json_data = []
        self.type = type.lower()
        self.links_path = "Links"
        self.article_path = "Articles"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        if self.type == "sitemap":
            self.start_urls.append("https://www.n-tv.de/sitemap.xml")
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
                self.logger.error(f"Error in __init__: {e}")
                raise InvalidDateRange("Invalid date format")

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
        self.logger.info("Parse function called on %s", response.url)
        try:
            if self.type == "sitemap":
                for sitemap in response.xpath(
                    "//sitemap:loc/text()",
                    namespaces={
                        "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"
                    },
                ):
                    for link in sitemap.getall():
                        r = requests.get(link, stream=True)
                        g = gzip.GzipFile(fileobj=BytesIO(r.content))
                        content = g.read()
                        soup = BeautifulSoup(content, "html.parser")

                        loc = soup.find_all("loc")
                        lastmod = soup.find_all("lastmod")

                        for particular_link, published_date in zip(loc, lastmod):
                            if 'thema' in particular_link:
                                continue
                            link = particular_link.text
                            published_at = published_date.text
                            date_only = datetime.strptime(
                                published_at[:10], "%Y-%m-%d"
                            ).date()

                            if self.start_date and date_only < self.start_date:
                                continue
                            if self.end_date and date_only > self.end_date:
                                continue

                            yield scrapy.Request(
                                link,
                                callback=self.make_sitemap,
                                meta={"published_at": published_at},
                            )
            elif self.type == "article":
                try:
                    self.logger.debug("Parse function called on %s", response.url)
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
                        response_data["country"] = ["Germany"]
                        response_data["time_scraped"] = [str(datetime.now())]
                        data["parsed_data"] = response_data
                    self.article_json_data.append(data)

                except BaseException as e:
                    print(f"Error: {e}")
                    self.logger.error(f"{e}")
        except BaseException as e:
            print(f"Error occurring while parsing sitemap {e} in parse function")
            self.logger.error(
                f"Error occurring while parsing sitemap {e} in parse function"
            )

    def make_sitemap(self, response):
        """
        Extracts URLs, titles, and publication dates from a sitemap response and saves them to a list.
        """
        try:
            published_date = response.meta["published_at"][:10]
            date_only = datetime.strptime(published_date, "%Y-%m-%d").date()

            if self.start_date and date_only < self.start_date:
                return
            if self.end_date and date_only > self.end_date:
                return

            link = response.url
            title = response.css(".article__headline::text").get()

            data = {
                "link": link,
                "title": title,
            }

            if self.start_date is None and self.end_date is None:
                today_date = datetime.today().strftime("%Y-%m-%d")
                today_date = datetime.strptime(today_date, "%Y-%m-%d").date()
                if date_only == today_date:
                    print("++++++++++++++++++++++++++++++++", date_only, today_date)
                    self.sitemap_data.append(data)
            else:
                self.sitemap_data.append(data)
        except BaseException as e:
            print(
                f"Error occurring while extracting link, title {e} in make_sitemap function"
            )
            self.logger.error(
                f"Error occurring while extracting link, title {e} in make_sitemap function"
            )

    def response_json(self, response) -> dict:

        parsed_json = {}
        main = self.get_main(response)
        if main:
            parsed_json["main"] = main

        misc = self.get_misc(response)
        if misc:
            parsed_json["misc"] = misc

        return parsed_json

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

    def response_data(self, response):
        response_data = {}
        pattern = r"[\r\n\t\"]+"

        article_title = response.css("h2 span.article__headline::text").get()
        if article_title:
            response_data["title"] = [re.sub(pattern, "", article_title).strip()]

        article_author = response.css(
            "span.article__infos span.article__author::text"
        ).get()
        if article_author:
            response_data["author"] = [
                {"@type": "Person", "name": re.sub(pattern, "", article_author).strip()}
            ]

        article_published = response.css("span.article__date::text").get()
        if article_published:
            response_data["published_at"] = [article_published]

        article_modified = response.css(
            'meta[name="last-modified"]::attr(content)'
        ).get()
        if article_modified:
            response_data["modified_at"] = [article_modified]

        article_description = response.css("p strong::text").get()
        if article_description:
            response_data["description"] = [article_description]

        article_publisher = self.get_main(response)
        if article_publisher:
            response_data["publisher"] = [article_publisher[0].get("publisher")]

        article_text = " ".join(response.css("p::text").getall())
        if article_text:
            response_data["text"] = [article_text]
        elif response.css("div.article__text::text").get():
            response_data["text"] = [
                re.sub(
                    pattern, "", response.css("div.article__text::text").get()
                ).strip()
            ]

        article_thumbnail = self.extract_thumbnail(response)
        if article_thumbnail:
            response_data["thumbnail_image"] = article_thumbnail

        article_video = response.css(
            "div.vplayer__video div video source::attr(src)"
        ).get()
        link = re.findall(r"http?.*?\.mp4", str(article_video))
        if link:
            response_data["embed_video_link"] = link

        article_tags = response.css("section.article__tags ul li a::text").getall()
        if article_tags:
            response_data["tags"] = article_tags

        article_lang = response.css("html::attr(lang)").get()
        if article_lang:
            response_data["language"] = [article_lang]

        return response_data

    def extract_thumbnail(self, response):
        video_article = response.css("div.vplayer div.vplayer__video")
        normal_article = response.css("div.article__media figure")
        data = []
        if normal_article:
            for i in normal_article:
                thumbnail_image = i.css("picture img::attr(src)").get()
                if thumbnail_image:
                    data.append(thumbnail_image)
        elif video_article:
            for j in video_article:
                thumbnail_image = j.css("img::attr(src)").get()
                if thumbnail_image:
                    data.append(thumbnail_image)
        return data

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
                json.dump(self.article_json_data, f, indent=4)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(NTvSpider)
    process.start()
