import re
import json
import gzip
import time
import scrapy
import requests
import logging
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from newton_scrapping.constants import SITEMAP_URL, TODAYS_DATE, LOGGER
from newton_scrapping import exceptions
from scrapy.utils.project import get_project_settings
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from newton_scrapping.items import ArticleData
from newton_scrapping.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    # get_raw_response,
    # get_parsed_data,
    # get_parsed_json,
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

class NTvSpider(scrapy.Spider):
    name = "bfm_tv"

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
        self.articles = []
        self.type = type.lower()
        self.main_json = None
        self.articles = url

        create_log_file()


        if self.type == "sitemap":
            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)
                self.start_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
                )
                self.end_date = (
                    datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
                )
                validate_sitemap_date_range(start_date, end_date)
        elif self.type == "article":
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
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

            elif self.type == "article":
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
                        response_data["country"] = ["France"]
                        response_data["time_scraped"] = [str(datetime.now())]
                        data["parsed_data"] = response_data

                    self.articles.append(data)

        except BaseException as e:
            print(f"Error while parse function: {e}")
            LOGGER.error(f"Error while parse function: {e}")

    def parse_sitemap(self, response):
        try:
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
                        link = particular_link.text
                        published_at = published_date.text
                        date_only = datetime.strptime(
                            published_at[:10], "%Y-%m-%d"
                        ).date()

                        if self.start_date and date_only < self.start_date:
                            continue
                        if self.end_date and date_only > self.end_date:
                            continue

                        if self.start_date is None and self.end_date is None:
                            if date_only != TODAYS_DATE:
                                continue

                        yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            meta={"published_at": published_at},
                        )
        except BaseException as e:
            LOGGER.error("Error while parsing sitemap: {}".format(e))
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):
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
            title = response.css("#contain_title::text").get()

            if title:
                data = {
                    "link": link,
                    "title": title,
                }

                if self.start_date is None and self.end_date is None:
                    if date_only == TODAYS_DATE:
                        self.articles.append(data)
                else:
                    self.articles.append(data)
        except BaseException as e:
            exceptions.SitemapArticleScrappingException(
                f"Error while filtering date wise: {e}"
            )
            LOGGER.error(f"Error while filtering date wise: {e}")


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
            self.main_json = data
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
        embedded_video_links = []
        text = []

        article_title = response.css("h1.content_title::text").get()
        if article_title:
            response_data["title"] = [re.sub(pattern, "", article_title).strip()]

        article_published = response.css("div#content_scroll_start time::text").get()
        if article_published:
            response_data["published_at"] = [article_published]

        article_description = response.css("div.chapo::text").get()
        if article_description:
            response_data["description"] = [article_description]

        article_text = " ".join(response.css("p::text").getall())
        print("\n\n\n\n ====>", article_text)
        if article_text:
            text.append(re.sub(pattern, "", article_text).strip())

        article_blockquote_text = " ".join(response.css("span::text").getall())
        if article_blockquote_text:
            text.append(re.sub(pattern, "", article_blockquote_text))

        if text:
            response_data["text"] = [" ".join(text)]

        article_author = response.css("span.author_name::text").get()
        if article_author:
            response_data["author"] = [
                {"@type": "Person", "name": re.sub(pattern, "", article_author).strip()}
            ]

        article_publisher = (self.main_json[1]).get("publisher")
        if article_publisher:
            response_data["publisher"] = [article_publisher]

        article_thumbnail = (self.main_json[1]).get("image").get("contentUrl")
        if isinstance(article_thumbnail, list):
            response_data["thumbnail_image"] = article_thumbnail

        thumbnail_video = (self.main_json[1]).get("video").get("embedUrl")
        if thumbnail_video:
            embedded_video_links.append(thumbnail_video)

        video_links = self.extract_videos(response)
        if video_links:
            embedded_video_links.append(video_links)

        if embedded_video_links:
            response_data["embed_video_link"] = embedded_video_links
        return response_data

    def extract_videos(self, response) -> list:

        options = Options()
        options.headless = True
        driver = webdriver.Chrome(options=options)

        driver.get(response.url)
        time.sleep(5)
        banner_button = driver.find_element(By.XPATH, "//div[@class='multiple didomi-buttons didomi-popup-notice-buttons']//button[2]")
        if banner_button:
            banner_button.click()
            time.sleep(2)
            scroll = driver.find_elements(By.XPATH, "//p")
            for i in scroll:
                driver.execute_script("window.scrollTo(" + str(i.location["x"]) + ", " + str(i.location["y"]) + ")")
            videos = driver.find_elements(By.XPATH, "//div[@class='video_block']//video-js//video[@class='vjs-tech']")
            if videos:
                data = {}
                for i in videos:
                    try:
                        data["videos"] += [i.get_attribute("src").replace("blob:", "")]
                    except:
                        data["videos"] = [i.get_attribute("src").replace("blob:", "")]
        return data

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


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(NTvSpider)
    process.start()
