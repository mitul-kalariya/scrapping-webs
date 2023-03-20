"""Spider to scrap Indian Express news website"""

# import itertools
import itertools
import json
import logging
from datetime import datetime
import os

import scrapy

# from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from scrapy.loader import ItemLoader

# from scrapy.utils.project import get_project_settings
from newton_scrapping.items import (
    IndianNewsArticleRawResponse,
    IndianNewsArticleRawParsedJson,
    AricleData,
)
from newton_scrapping.utils import based_on_type, date_range

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


class IndianexpressSpider(scrapy.Spider):
    """Spider"""

    name = "indian_express"
    start_urls = ["https://indianexpress.com/"]
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(IndianexpressSpider, self).__init__(*args, **kwargs)

        try:
            self.start_urls = []
            self.articles = []
            self.date_range_lst = []
            self.article_url = url
            self.error_msg_dict = {}
            self.type = type
            self.scrape_start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.scrape_end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )

            self.current_date, self.date_range_lst = based_on_type(
                self.type, self.scrape_start_date, self.scrape_end_date, url
            )
            if self.current_date:
                self.scrape_start_date = self.scrape_end_date = self.current_date
            self.start_urls.append(
                url
                if self.type == "article"
                else "https://indianexpress.com/sitemap.xml"
            )

        except Exception as exception:
            self.error_msg_dict["error_msg"] = (
                "Error occured while taking type, url, start_date and end_date args. "
                + str(exception)
            )
            self.log(
                "Error occured while taking type, url, start_date and end_date args. "
                + str(exception),
                level=logging.ERROR,
            )

    def parse(self, response, **kwargs):
        if self.error_msg_dict:
            raise CloseSpider(self.error_msg_dict.get("error_msg"))

        if "sitemap.xml" in response.url:
            for single_date in date_range(self.scrape_start_date, self.scrape_end_date):
                try:
                    self.logger.debug("Parse function called on %s", response.url)
                    # url info : https://indianexpress.com/sitemap.xml?yyyy=2023&mm=03&dd=10
                    yield scrapy.Request(
                        f"""https://indianexpress.com/sitemap.xml?yyyy={single_date.year}&mm={single_date.month}&dd={single_date.day}""",
                        callback=self.parse_sitemap,
                    )
                except Exception as exception:
                    self.log(
                        f"Error occured while iterating sitemap url. {str(exception)}",
                        level=logging.ERROR,
                    )
        else:
            yield self.parse_article(response)

    def parse_sitemap(self, response):
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        """
        try:
            for article_url in (
                Selector(response, type="xml")
                .xpath("//sitemap:loc/text()", namespaces=self.namespace)
                .getall()
            ):
                yield scrapy.Request(article_url, callback=self.parse_sitemap_article)
        except Exception as exception:
            self.log(
                "Error occured while scrapping urls from given sitemap url. "
                + str(exception),
                level=logging.ERROR,
            )

    def parse_sitemap_article(self, response):
        """
        parse sitemap article and  scrap title and link
        """
        try:
            # data = IndianNewsSitemap()
            # data["title"] = response.css("h1.native_story_title::text").get()
            # data["link"] = response.url
            if title := response.css("h1.native_story_title::text").get():
                data = {"link": response.url, "title": title}
            # yield data
            self.articles.append(data)
        except Exception as exception:
            self.log(
                f"Error occured while scraping sitemap's article. {str(exception)}",
                level=logging.ERROR,
            )

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        """
        try:
            indian_news_article_raw_response_loader = ItemLoader(
                item=IndianNewsArticleRawResponse(), response=response
            )
            aricle_data_loader = ItemLoader(item=AricleData(), response=response)
            indian_news_article_raw_parsed_json_loader = ItemLoader(
                item=IndianNewsArticleRawParsedJson(), response=response
            )
            parsed_json_main = response.css('script[type="application/ld+json"]::text')
            parsed_json_misc = response.css('script[type="application/json"]::text')

            indian_news_article_raw_response_loader.add_value(
                "content_type", response.headers.get("Content-Type").decode("utf-8")
            )
            indian_news_article_raw_response_loader.add_value("content", response.text)
            if parsed_json_main:
                parsed_json_main = [
                    json.loads(data) for data in parsed_json_main.getall()
                ]
                indian_news_article_raw_parsed_json_loader.add_value(
                    "main", parsed_json_main
                )
            if parsed_json_misc:
                parsed_json_misc = [
                    json.loads(data) for data in parsed_json_misc.getall()
                ]
                indian_news_article_raw_parsed_json_loader.add_value(
                    "misc", parsed_json_misc
                )
            aricle_data_loader.add_value(
                "raw_response",
                dict(indian_news_article_raw_response_loader.load_item()),
            )
            aricle_data_loader.add_value(
                "parsed_json",
                dict(indian_news_article_raw_parsed_json_loader.load_item()),
            )
            json_ld_blocks = []
            blocks = response.css('script[type="application/ld+json"]::text').getall()

            for block in blocks:
                if json.loads(block).get("author", None):
                    author_type = (
                        json.loads(block).get("author", None)[0].get("@type", None)
                    )
                if json.loads(block).get("publisher", None):
                    publisher_type = (
                        json.loads(block).get("publisher", None).get("@type", None)
                    )
                    publisher_id = (
                        json.loads(block).get("publisher", None).get("url", None)
                    )

                json_ld_blocks.append(json.loads(block))

            logo_height = response.css(
                "#wrapper div.main-header__logo img::attr(height)"
            ).get()
            logo_width = response.css(
                "#wrapper div.main-header__logo img::attr(width)"
            ).get()
            video_url = response.css("span.embed-youtube iframe::attr(src)").getall()
            images = response.css("span.custom-caption > img::attr(src)").getall()
            published_date = response.css("div.ie-first-publish span::text").getall()
            modified_date = (
                response.css("div.editor-date-logo div span::text").getall()
                or response.css("span.updated-date::attr(content)").getall()
            )
            if not modified_date:
                modified_date = None

            parsed_data_dict = {
                "author": [
                    {
                        "@type": author_type,
                        "name": response.css("div.editor div a::text").get(),
                        "url": response.css("div.editor div a::attr(href)").get(),
                    }
                ],
                "description": response.css("h2.synopsis::text").get(),
                "modified_at": modified_date,
                "published_at": published_date,
                # "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                "publisher": [
                    {
                        "@id": publisher_id,
                        "@type": publisher_type,
                        "name": response.css(
                            "#wrapper div.main-header__logo img::attr(title)"
                        ).get(),
                        "logo": {
                            "type": "ImageObject",
                            "url": response.css(
                                "#wrapper div.main-header__logo img::attr(src)"
                            ).get(),
                            "width": {
                                "type": "Distance",
                                "name": f"{logo_width} px",
                            },
                            "height": {
                                "type": "Distance",
                                "name": f"{logo_height} px",
                            },
                        },
                    }
                ],
                "text": response.css("div#pcl-full-content p::text").getall(),
                "title": response.css("div.heading-part  h1::text").get(),
                "images": [
                    {"link": img, "caption": cap}
                    for img, cap in itertools.zip_longest(
                        response.css("span.custom-caption > img::attr(src)").getall(),
                        response.css("span.ie-custom-caption::text").getall()
                        + response.css("span.custom-caption::text").getall(),
                        fillvalue=None,
                    )
                ],
                "video": {"link": video_url},
                "section": response.css("ol.m-breadcrumb li a::text").getall(),
                "tags": response.css("div.storytags ul li a::text").getall(),
            }

            if not video_url:
                parsed_data_dict.pop("video")
            if not images:
                parsed_data_dict.pop("images")

            aricle_data_loader.add_value("parsed_data", parsed_data_dict)

            self.articles.append(dict(aricle_data_loader.load_item()))

        except Exception as exception:
            self.log(
                "Error occured while scrapping an article for this link {response.url}."
                + str(exception),
                level=logging.ERROR,
            )

    def closed(self, response):
        """
        store all scrapped data into json file with given date in filename
        """
        try:
            if not self.articles:
                self.log("No articles or sitemap url scapped.", level=logging.INFO)
            else:
                folder_structure = ""
                if self.type == "sitemap":
                    folder_structure = "Links"
                    filename = f'{self.name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
                elif self.type == "article":
                    folder_structure = "Article"
                    filename = f'{self.name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
                if not os.path.exists(folder_structure):
                    os.makedirs(folder_structure)
                with open(
                    f"{folder_structure}/{filename}.json", "w", encoding="utf-8"
                ) as file:
                    json.dump(self.articles, file, indent=4)
        except Exception as exception:
            self.log(
                f"Error occured while writing json file{str(exception)}",
                level=logging.ERROR,
            )