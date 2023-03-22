import re
import json
from datetime import datetime
import os
import scrapy
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    filename="logs.log",
    filemode="a",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()


class InvalidDateRange(Exception):
    pass


class ArdNewsSpider(scrapy.Spider):
    # Assigning spider name
    name = "ard_news"

    # Initializing the spider class with site_url and category parameters
    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = []
        self.sitemap_data = []
        self.article_json_data = []
        self.start_urls = []
        self.sitemap_json = {}
        self.type = type.lower()
        self.domain_name = "https://www.tagesschau.de"
        self.today_date = datetime.today().date()
        self.links_path = "Links"
        self.article_path = "Article"

        if not os.path.exists(self.links_path):
            os.makedirs(self.links_path)
        if not os.path.exists(self.article_path):
            os.makedirs(self.article_path)

        if self.type == "sitemap":
            self.start_urls.append("https://www.tagesschau.de/")
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
                if (
                        self.start_date
                        and self.end_date
                        and self.start_date > self.today_date
                ):
                    raise InvalidDateRange(
                        "start_date should not be greater than today_date"
                    )
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
        if self.type == "sitemap":
            if self.start_date and self.end_date:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)
            else:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

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
                response_data["country"] = ["Germany"]
                response_data["time_scraped"] = [str(datetime.now())]
                data["parsed_data"] = response_data

            self.article_json_data.append(data)

    def parse_sitemap(self, response):
        try:
            for link in response.css("a"):
                url = link.css("::attr(href)").get()
                title = link.css("a::text").get().replace("\n", "")
                if url:
                    if url.startswith(("#", "//")) or url in [
                        "https://www.ard.de",
                        "https://www.tagesschau.de",
                        "https://wetter.tagesschau.de/",
                    ]:
                        continue
                    if url.startswith("/"):
                        url = self.domain_name + url
                if url is not None and title is not None:
                    title = title.strip()

                    if not title and title:
                        self.sitemap_json["title"] = (
                            link.css(".teaser-xs__headline::text , .teaser__headline::text")
                            .get()
                            .replace("\n", "")
                            .replace(" ", "")
                        )
                    # Storing the title in the sitemap_json dictionary
                    elif title:
                        self.sitemap_json["title"] = title
                    # Sending a request to the parse_articlewise_get_date method
                    yield scrapy.Request(url, callback=self.parse_articlewise_get_date)
        except BaseException as e:
            print(f"Error while parsing sitemap: {e}")
            self.logger.error("Error while parsing sitemap: {}".format(e))

    def parse_articlewise_get_date(self, response):
        try:
            for article in response.css(".teaser__link"):
                title = article.css(".teaser__headline::text").get()
                link = article.css("a::attr(href)").get()

                yield scrapy.Request(
                    link, callback=self.parse_date, meta={"link": link, "title": title}
                )
        except BaseException as e:
            print(f"Error while filtering date wise: {e}")
            self.logger.error("Error while filtering date wise: {}".format(e))

    def parse_date(self, response):
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
                    if date_obj == self.today_date:
                        self.sitemap_data.append(data)
                else:
                    self.sitemap_data.append(data)

    def response_data(self, response) -> dict:
        pattern = r"[\r\n\t\"]+"
        main_dict = {}

        # extract author info
        authors = self.extract_author_info(response.css("div.copytext-element-wrapper"))
        if authors:
            main_dict["author"] = authors

        # extract main headline of article
        title = response.css("span.seitenkopf__headline--text::text").get()
        if title:
            main_dict["title"] = [title]

        publisher = self.get_main(response)
        if publisher:
            main_dict["publisher"] = [publisher[0].get("publisher")]

        # extract the date published at
        published_at = response.css("div.metatextline::text").get()
        if published_at:
            clean_time = re.sub(pattern, "", published_at).strip()
            main_dict["published_at"] = [clean_time]

        descryption = response.css("p strong::text").get()
        if descryption:
            main_dict["description"] = [re.sub(pattern, "", descryption).strip()]

        # extract the description or read text of the article
        text = response.css("p.textabsatz::text").getall()
        text = [re.sub(pattern, "", i) for i in text]
        main_dict["text"] = [" ".join(list(filter(None, text)))]

        # extract the thumbnail image
        thumbnail_image = response.css(
            "picture.ts-picture--topbanner .ts-image::attr(src)"
        ).get()
        if thumbnail_image:
            main_dict["thumbnail_image"] = [
                "https://www.tagesschau.de/" + thumbnail_image
            ]

        # extract video files if any
        video = self.extract_all_videos(response.css("div.copytext__video"))
        if video:
            main_dict["embed_video_link"] = video

        # extract tags associated with article
        tags = response.css("ul.taglist li a::text").getall()
        if tags:
            main_dict["tags"] = tags

        article_lang = response.css("html::attr(lang)").get()
        if article_lang:
            main_dict["language"] = [article_lang]

        return main_dict

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

    def extract_audio_info(self, response) -> list:
        info = []
        for child in response:
            audio = child.css("div.ts-mediaplayer::attr(data-config)").get()
            adict = {}
            if audio:
                audio_link = re.findall(r"http?.*?\.mp3", audio)[0]
                if audio_link:
                    adict["link"] = audio_link
                    audio_title = child.css("h3.copytext__audio__title::text").get()
                    if audio_title:
                        adict["caption"] = audio_title
                    info.append(adict)
        return info

    def extract_author_info(self, response) -> list:
        info = []
        if response:
            for child in response:
                a_dict = {}
                auth_name = child.css("span.id-card__name::text").get()
                if auth_name:
                    a_dict["@type"] = "Person"
                    a_dict["name"] = auth_name.strip()
                    link = child.css("a.id-card__twitter-id::attr(href)").get()
                    if link:
                        a_dict["url"] = link
                    info.append(a_dict)

            return info

    def extract_all_title(self, response) -> list:
        titles = []
        for single_title in response:
            title = single_title.css("span::text").get()
            if title in ["", None]:
                title = single_title.css("h2.meldung__subhead::text").get()
            titles.append(title)
        return titles

    def extract_all_videos(self, response) -> list:
        info = []
        for child in response:
            video = child.css("div.ts-mediaplayer::attr(data-config)").get()
            if video:
                video_link = re.findall(r"http?.*?\.mp4", video)[0]
                if video_link:
                    info.append(video_link)
        return info

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
