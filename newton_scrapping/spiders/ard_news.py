import re
import scrapy
import logging
from newton_scrapping.constants import BASE_URL, TODAYS_DATE, LOGGER
from newton_scrapping import exceptions
from datetime import datetime
from abc import ABC, abstractmethod
from scrapy.loader import ItemLoader
from newton_scrapping.items import ArticleData
from newton_scrapping.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    remove_empty_elements,
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


class ArdNewsSpider(scrapy.Spider, BaseSpider):
    # Assigning spider name
    name = "ard_news"

    # Initializing the spider class with site_url and category parameters
    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = []
        self.articles = []
        self.start_urls = []
        self.sitemap_json = {}
        self.type = type.lower()

        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append(BASE_URL)
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

    def parse(self, response):
        if self.type == "sitemap":
            if self.start_date and self.end_date:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)
            else:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

        elif self.type == "article":
            breakpoint()
            article_data = self.parse_article(response)
            breakpoint()
            self.articles.append(article_data)

    def parse_article(self, response) -> list:
        articledata_loader = ItemLoader(item=ArticleData(), response=response)        
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        response_data["country"] = ["Germany"]
        response_data["time_scraped"] = [str(datetime.now())]
        
        data = {}

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value("parsed_json",response_json,)
        articledata_loader.add_value(
                "parsed_data", response_data)
        

        return dict(articledata_loader.load_item())

    def parse_sitemap(self, response):
        try:
            for link in response.css("a"):
                url = link.css("::attr(href)").get()
                title = link.css("a::text").get().replace("\n", "")
                if url:
                    if url.startswith(("#", "//")) or url in [
                        "https://www.ard.de",
                        "https://wetter.tagesschau.de/",
                        BASE_URL,
                    ]:
                        continue
                    if url.startswith("/"):
                        url = BASE_URL + url
                if url is not None and title is not None:
                    title = title.strip()

                    if not title and title:
                        self.sitemap_json["title"] = (
                            link.css(
                                ".teaser-xs__headline::text , .teaser__headline::text"
                            )
                            .get()
                            .replace("\n", "")
                            .replace(" ", "")
                        )
                    # Storing the title in the sitemap_json dictionary
                    elif title:
                        self.sitemap_json["title"] = title

                    # Sending a request to the parse_articlewise_get_date method
                    yield scrapy.Request(url, callback=self.parse_sitemap_article)
        except BaseException as e:
            LOGGER.error("Error while parsing sitemap: {}".format(e))
            exceptions.SitemapScrappingException(f"Error while parsing sitemap: {e}")

    def parse_sitemap_article(self, response):
        try:
            for article in response.css(".teaser__link"):
                title = article.css(".teaser__headline::text").get()
                link = article.css("a::attr(href)").get()

                yield scrapy.Request(
                    link,
                    callback=self.parse_sitemap_datewise,
                    meta={"link": link, "title": title},
                )
        except BaseException as e:
            exceptions.SitemapArticleScrappingException(f"Error while filtering date wise: {e}")
            LOGGER.error("Error while filtering date wise: {}".format(e))

    def parse_sitemap_datewise(self, response):
        link = response.meta["link"]
        title = response.meta["title"]
        published_date = response.css(".metatextline::text").get()
        if isinstance(published_date, str):
            match = re.search(r"\d{2}\.\d{2}\.\d{4}", published_date)
            if match:
                date_obj = datetime.strptime(match.group(), "%d.%m.%Y").date()

                if self.start_date and date_obj < self.start_date:
                    return

                if self.end_date and date_obj > self.end_date:
                    return

                data = {
                    "link": link,
                    "title": title.replace("\n", "").replace('"', "").strip(),
                }
                if self.start_date is None and self.end_date is None:
                    if date_obj == TODAYS_DATE:
                        self.articles.append(data)
                else:
                    self.articles.append(data)

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
            exceptions.ExportOutputFileException(f"Error occurred while writing json file{str(exception)} - {reason}")
            self.log(
                f"Error occurred while writing json file{str(exception)} - {reason}",
                level=logging.ERROR,
            )
