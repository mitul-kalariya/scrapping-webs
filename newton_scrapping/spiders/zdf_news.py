import re
import json
import scrapy
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from scrapy.http import XmlResponse
from scrapy.selector import Selector
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import os


class InvalidDateRange(Exception):
    pass


class ZdfNewsSpider(scrapy.Spider):
    name = "zdf_news"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = []
        self.sitemap_data = []
        self.article_json_data = []
        self.type = type.lower()
        self.today_date = datetime.today().strftime("%Y-%m-%d")
        self.links_path = "Links"
        self.article_path = "Articles"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        if self.type == "sitemap":
            self.start_urls.append("https://www.zdf.de/sitemap.xml")
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
                self.logger.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

    def parse(self, response):
        try:
            if self.type == "sitemap":
                if self.start_date and self.end_date:
                    yield scrapy.Request(response.url, callback=self.parse_by_date)
                else:
                    yield scrapy.Request(response.url, callback=self.parse_by_date)
            elif self.type == "article":

                response_json, response_data = self.scrap_site(response)
                final_data = {
                    "raw_response": {
                        "content_type": "text/html; charset=utf-8",
                        "content": response.css("html").get(),
                    },
                }
                if response_json:
                    final_data["parsed_json"] = response_json
                if response_data:
                    final_data["parsed_data"] = response_data
                    response_data["country"] = ["Germany"]
                    response_data["time_scraped"] = [str(datetime.now())]
                self.article_json_data.append(final_data)

        except BaseException as e:
            print(f"Error: {e}")
            self.logger.error(f"{e}")

    def parse_by_date(self, response):
        xmlresponse = XmlResponse(
            url=response.url, body=response.body, encoding="utf-8"
        )
        xml_selector = Selector(xmlresponse)
        xml_namespaces = {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for sitemap in xml_selector.xpath(
            "//xmlns:loc/text()", namespaces=xml_namespaces
        ):
            for link in sitemap.getall():
                yield scrapy.Request(link, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        links = response.xpath("//n:loc/text()", namespaces=namespaces).getall()
        published_date = response.xpath('//*[local-name()="lastmod"]/text()').getall()

        for link, pub_date in zip(links, published_date):
            published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
            today_date = datetime.strptime(self.today_date, "%Y-%m-%d").date()
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
            elif today_date == published_at:
                yield scrapy.Request(
                    link,
                    callback=self.parse_sitemap_link_title,
                    meta={"link": link, "published_date": published_at},
                )
            else:
                continue

    def parse_sitemap_link_title(self, response):
        link = response.meta["link"]
        published_date = response.meta["published_date"]
        title = response.css("h2#main-content").get()
        pattern = r"[\r\n\t\</h2>\<h2>]+"
        if title:
            title = re.sub(pattern, "", title.split("</span>")[2]).strip()
            if self.start_date and published_date < self.start_date:
                return
            if self.start_date and published_date > self.end_date:
                return
            data = {
                "link": link,
                "title": title,
            }
            self.sitemap_data.append(data)

    def scrap_site(self, response):
        """generate required data as response json and response data

        Args:
            response (obj): site response object

        Returns:
            dict: returns 2 dictionary parsed_json and parsed_data
        """

        response_json, response_data = {}, {}

        main_data = self.get_main(response)
        if main_data:
            response_json["main"] = main_data
        misc_data = self.get_misc(response)
        if misc_data:
            response_json["misc"] = misc_data

        pattern = r"[\r\n\t\</h2>\<h2>]+"

        topline = response.css("span.news-overline::text").get()
        if topline:
            response_data["description"] = [topline]

        title = response.css("h2#main-content").get()
        if title:
            title = re.sub(pattern, "", title.split("</span>")[2]).strip()
            response_data["title"] = [title]

        published_on = response.css("dd.postdate time::text").get()
        if published_on:
            response_data["published_on"] = [published_on]

        author = response.css("div.author-wrap div span::text").get()
        if author:
            author = re.sub(pattern, "", author).strip()
            response_data["author"] = [{"@type": "Person", "name": author}]

        publisher = self.extract_publisher(response)
        if publisher:
            response_data["publisher"] = [publisher]

        display_text = response.css("p::text").getall()
        if display_text:
            response_data["text"] = [
                " ".join([re.sub("[\r\n\t]+", "", x).strip() for x in display_text])
            ]

        images = self.extract_images(response)
        if images:
            try:
                response_images = images[1:]
                if response_images:
                    response_data["images"] = response_images

            except BaseException as e:
                self.logger.error(f"{e}")
                print(f"Error: {e}")

        thumbnail_image = images[0].get("link")
        if thumbnail_image:
            response_data["thumbnail_image"] = [thumbnail_image]

        article_lang = response.css("html::attr(lang)").get()
        if article_lang:
            response_data["language"] = [article_lang]

        return response_json, response_data

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

    def extract_images(self, response, parsed_json=False) -> list:
        images = response.css("figure.content-image")
        data = []
        for image in images:
            temp_dict = {}
            link = image.css("img::attr(data-src)").get()
            caption = image.css("figcaption small::text").get()
            if parsed_json:
                if link:
                    temp_dict["@type"] = "ImageObject"
                    temp_dict["link"] = link
            else:
                if link:
                    temp_dict["link"] = link
                    if caption:
                        temp_dict["caption"] = caption
            data.append(temp_dict)
        return data

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
            misc_resp = self.get_misc(response)
            publisher = misc_resp[0].get("publisher")
            logo_url = publisher.get("logo").get("url")
            img_response = requests.get(logo_url)
            width, height = Image.open(BytesIO(img_response.content)).size
            a_dict = {
                "@id": "zdf.de",
                "@type": "NewsMediaOrganization",
                "name": "Zweites Deutsches Fernsehen",
                "logo": {
                    "@type": "ImageObject",
                    "url": logo_url,
                    "width": {"@type": "Distance", "name": str(width) + " px"},
                    "height": {"@type": "Distance", "name": str(height) + " px"},
                },
            }

            return a_dict
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

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
    process.crawl(ZdfNewsSpider)
    process.start()
