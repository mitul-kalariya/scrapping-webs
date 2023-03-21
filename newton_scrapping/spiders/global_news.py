import re
import json
from io import BytesIO
from datetime import datetime
import os
import scrapy
import requests
from PIL import Image
from lxml import etree
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


class InvalidDateRange(Exception):
    pass


class GlobalNewsSpider(scrapy.Spider):
    name = "global_news"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
            A spider to crawl globalnews.ca for news articles. The spider can be initialized with two modes:
            1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca
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
        self.article_path = "Articles"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        if self.type == "sitemap":
            self.start_urls.append("https://globalnews.ca/news-sitemap.xml")
            try:
                self.start_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date()
                    if start_date
                    else None
                )
                self.end_date = (
                    datetime.strptime(end_date, "%Y-%m-%d").date()
                    if end_date
                    else None
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
        """Parses the response object and extracts data based on the type of object.
            Returns:
                generator: A generator that yields scrapy.Request objects to be further parsed by other functions.
        """
        if self.type == "sitemap":
            if self.start_date and self.end_date:
                self.logger.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_sitemap)
            else:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

        elif self.type == "article":
            try:
                self.logger.debug("Parse function called on %s", response.url)
                response_json = self.response_json(response)
                response_data = self.response_data(response)
                data = {'raw_response': {
                    "content_type": "text/html; charset=utf-8",
                    "content": response.css('html').get(),
                }, }
                if response_data:
                    data["parsed_json"] = response_json
                if response_data:
                    data["parsed_data"] = response_data

                self.article_json_data.append(data)

            except BaseException as e:
                print(f"Error: {e}")
                self.logger.error(f"{e}")

    def parse_sitemap(self, response):
        """
            Extracts URLs, titles, and publication dates from a sitemap response and saves them to a list.
        """
        root = etree.fromstring(response.body)
        urls = root.xpath(
            "//xmlns:loc/text()",
            namespaces={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
        )
        titles = root.xpath(
            "//news:title/text()",
            namespaces={"news": "http://www.google.com/schemas/sitemap-news/0.9"},
        )
        publication_dates = root.xpath(
            "//news:publication_date/text()",
            namespaces={"news": "http://www.google.com/schemas/sitemap-news/0.9"},
        )

        for url, title, pub_date in zip(urls, titles, publication_dates):
            published_at = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
            if self.start_date and published_at < self.start_date:
                return
            if self.start_date and published_at > self.end_date:
                return

            if self.start_date is None and self.end_date is None:
                if self.today_date in pub_date:
                    data = {
                        "url": url,
                        "title": title,
                    }
                    self.sitemap_data.append(data)
            else:
                data = {
                    "url": url,
                    "title": title,
                }
                self.sitemap_data.append(data)

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

            article_label = response.css("div#article-label a::text").get()
            if article_label:
                main_dict["category"] = [re.sub(pattern, "", article_label).strip()]

            headline = response.css("h1.l-article__title::text").getall()
            if headline:
                main_dict["title"] = headline

            authors = self.extract_author(response)
            if authors:
                main_dict["author"] = authors

            published_on = response.css(
                "div.c-byline__datesWrapper > div > div.c-byline__date--pubDate > span::text"
            ).get()
            if published_on:
                published_on = published_on.strip("Posted ")
                main_dict["published_at"] = [published_on]

            updated_on = response.css(
                "div.c-byline__datesWrapper > div > div.c-byline__date--modDate > span::text"
            ).get()
            if updated_on:
                updated_on = updated_on.strip("Updated ")
                main_dict["modified_at"] = [updated_on]

            thumbnail_image = self.extract_thumbnail_image(response)
            if thumbnail_image:
                main_dict["thumbnail_image"] = thumbnail_image

            article_text = response.css("p::text").getall()
            if article_text:
                main_dict["text"] = [" ".join(article_text)]

            tags = self.extract_tags(response)
            if tags:
                main_dict["tags"] = tags

            images = self.extract_images_sc(response)
            if images:
                main_dict["images"] = images

            videos = self.extract_all_videos(response)
            if videos:
                main_dict["embed_video_link"] = videos

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
                "@id": "globalnews.ca",
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
            info = response.css("div#article-byline")
            pattern = r"[\r\n\t\"]+"
            data = []
            if info:
                for i in info:
                    temp_dict = {}
                    temp_dict["@type"] = "Person"
                    name = i.css("div.c-byline__attribution span a::text").get()
                    if name:
                        name = re.sub(pattern, "", name).strip()
                        temp_dict["name"] = name.strip("By")

                    else:
                        temp_dict["name"] = "Staff"

                    link = i.css("div.c-byline__attribution span a::attr(href)").get()
                    if link:
                        temp_dict["url"] = link
                    # temp_dict["organization"] = re.sub(
                    #     pattern, "", i.css("span.c-byline__source::text").get()
                    # ).strip()
                    """while reviewing if you feel that this data can be useful please uncomment it
                        it states from which organization the author is"""

                    data.append(temp_dict)
                return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def extract_tags(self, response) -> list:
        """
        Extracts lables associated to the news article in form of a list of dictionary
        containing name of the tag and the corrosponding link to the tag

        Parameters:
            response (scrapy.http.Response): The response object containing the HTML of the article page.
        Returns:
            a list of dictionary with link and name combination
        """
        try:
            info = response.css("div.c-tags__body a")
            data = []
            for i in info:
                temp_dict = {}
                temp_dict["tag"] = i.css("a::text").get()
                temp_dict["url"] = i.css("a::attr(href)").get()
                if temp_dict["url"] == "#":
                    pass
                else:
                    data.append(temp_dict)
            return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def extract_all_videos(self, response) -> list:
        """
        extracting all the videos available from article
        parameters:
            response: html response
        returns:
            a list of dictionary containing object type link and decryption
        """
        try:
            data = []
            thumbnail_video = response.css("figure.l-article__featured")
            for video in thumbnail_video:
                link = video.css(".c-video::attr(data-displayinline)").get()
                if link:
                    data.append(link)

            videos = response.css("div.c-video.c-videoPlay")
            for video in videos:
                link = video.css("div::attr(data-displayinline)").get()
                if link:
                    data.append(link)
            return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def extract_images_sc(self, response) -> list:
        """extracting image links from provided response

        Args:
            response (_type_): html page object

        Returns:
            list: list of images inside the article
        """
        try:
            images = response.css("figure.c-figure--alignnone")
            pattern = r"[\r\n\t]+"
            data = []
            if images:
                for image in images:
                    temp_dict = {}
                    link = image.css("img::attr(data-src)").get()
                    caption = image.css(
                        "figcaption.c-figure__caption.c-caption span::text"
                    ).get()
                    if link:
                        temp_dict["url"] = link
                        if caption:
                            temp_dict["caption"] = re.sub(pattern, "", caption).strip()
                        data.append(temp_dict)
                return data
        except BaseException as e:
            self.logger.error(f"Error: {e}")
            print(f"Error: {e}")

    def extract_thumbnail_image(self, response) -> list:
        """extracting thumbnail image from application+ld/json data in main function

        Args:
            response (obj): page_object

        Returns:
            list: list of thumbnail images
        """
        image = self.get_main(response)
        thumbnail_image = []
        thumbnail_image.append(image[0].get("thumbnailUrl"))
        return thumbnail_image

    def closed(self, response):
        """
            Method called when the spider is finished scraping.
            Saves the scraped data to a JSON file with a timestamp
            in the filename.
        """
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
        if self.type == "sitemap":
            file_name = f"{self.links_path}/{self.name}-{'sitemap'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.sitemap_data, f, indent=4)

        if self.type == "article":
            file_name = f"{self.article_path}/{self.name}-{'article'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.article_json_data, f, indent=4)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(GlobalNewsSpider)
    process.start()
