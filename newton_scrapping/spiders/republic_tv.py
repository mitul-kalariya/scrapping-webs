import re
import json
import scrapy
import requests
import logging
from PIL import Image
from io import BytesIO
from dateutil import parser
from datetime import datetime

# Setting the threshold of logger to DEBUG
LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"

logging.basicConfig(
    level=logging.DEBUG,
    filename="logs.log",
    format=LOG_FORMAT,
    filemode="a",
)

# Creating an object
logger = logging.getLogger()


class InvalidDateRange(Exception):
    pass

class RepublicTvSpider(scrapy.Spider):
    name = "republic_tv"

    def __init__(
            self,
            type=None,
            start_date=None,
            url=None,
            end_date=None,
            **kwargs
    ):
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
        self.today_date = datetime.today().strftime('%Y-%m-%d')

        if self.type == "sitemap":
            self.start_urls.append("https://www.republicworld.com/sitemap.xml")
            try:
                self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
                self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

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
        if self.type == 'sitemap':
            if self.start_date != None and self.end_date != None:
                self.logger.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_by_date)
            else:
                self.logger.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_by_date)
        elif self.type == 'article':
            try:
                self.logger.debug("Parse function called on %s", response.url)
                current_url = response.request.url
                response_data = self.response_data(response)
                response_json = self.response_json(response, current_url)
                final_data = {
                    "raw_response": {
                        "content_type": "text/html; charset=utf-8",
                        "content": response.css("html").get(),
                    },
                    "parsed_json": response_json,
                    "parsed_data": response_data,
                }
                self.article_json_data.append(final_data)
            except BaseException as e:
                print(f"Error: {e}")
                self.logger.error(f"{e}")

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
                        if self.start_date == None and self.end_date == None:
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
            The function extracts the links from the sitemap and sends a request to scrape each link using the `parse_sitemap_link_title` callback method.
            The function also extracts the publication date of the sitemap, if available, and passes it along as a meta parameter in each request.
        """ # noqa
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

    def response_json(self, response, current_url) -> dict:
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
        parsing_dict = {}
        parsing_dict["main"] = {
            "@context": "https://bharat.republicworld.com/",
            "@type": "NewsArticle",
            "mainEntityOfPage": {"@type": "WebPage", "@id": current_url},
        }
        main_dict = parsing_dict["main"]

        headline = response.css("h1.story-title::text").get()
        if headline:
            main_dict["headline"] = headline

        published_on = self.extract_publishd_on(response)
        if published_on:
            main_dict["datePublished"] = published_on

        last_updated = self.extract_lastupdated(response)
        if last_updated:
            main_dict["dateModified"] = last_updated

        publisher = self.extract_publisher(response)
        if publisher:
            main_dict["publisher"] = publisher

        description = response.css("h2.story-description::text").get()
        if description:
            main_dict["description"] = description

        authors = self.extract_author(response)
        if authors:
            main_dict["author"] = authors

        article_images = self.extract_all_images(response)
        if article_images:
            main_dict["image"] = article_images

        parsing_dict["misc"] = self.get_misc(response)

        return parsing_dict

    def get_misc(self, response):
        data = []
        misc = response.css('script[type="application/ld+json"]::text').getall()
        for block in misc:
            data.append(json.loads(block))
        return data

    def response_data(self, response) -> dict:
        """
        Extracts data from a news article webpage and returns it in a dictionary format.

        Parameters:
        response (scrapy.http.Response): A scrapy response object of the news article webpage.

        Returns:
        dict: A dictionary containing the extracted data from the webpage, including:
            - 'breadcrumbs': (list) The list of breadcrumb links to the article, if available.
            - 'published_on': (str) The date and time the article was published.
            - 'last_updated': (str) The date and time the article was last updated, if available.
            - 'headline': (str) The headline of the article.
            - 'description': (str) The description of the article, if available.
            - 'publisher': (str) The name of the publisher of the article.
            - 'authors': (list) The list of authors of the article, if available.
            - 'video': (str) The video URL of the article, if available.
            - 'thumbnail_image': (str) The URL of the thumbnail image of the article, if available.
            - 'subheadings': (list) The list of subheadings in the article, if available.
            - 'text': (list) The list of text paragraphs in the article.
            - 'images': (list) The list of image URLs in the article, if available.
        """
        main_dict = {}

        authors = self.extract_author(response)
        if authors:
            main_dict["author"] = authors

        last_updated = self.extract_lastupdated(response)
        if last_updated:
            main_dict["modified_at"] = [last_updated]

        published_on = self.extract_publishd_on(response)
        if published_on:
            main_dict["published_at"] = [published_on]
        
        description = response.css("h2.story-description::text").get()
        if description:
            main_dict["description"] = [description]

        publisher = self.extract_publisher(response)
        if publisher:
            main_dict["publisher"] = publisher

        article_text = response.css("section p::text").getall()
        if article_text:
            main_dict["text"] = [" ".join(article_text)]

        thumbnail = self.extract_thumnail(response)
        if thumbnail:
            main_dict["thumbnail_image"] = thumbnail

        headline = response.css("h1.story-title::text").get().strip()
        if headline:
            main_dict["title"] = [headline]

        article_images = self.extract_all_images(response)
        if article_images:
            main_dict["images"] = article_images

        video = self.extract_video(response)
        if video:
            main_dict["embed_video_link"] = video

        return main_dict

    def extract_breadcrumbs(self, response) -> list:
        """
        Parameters:
        response:
            scrapy.http.Response object of the web page from which to extract the breadcrumb information.

        Returns:
            A list of dictionaries with the breadcrumb information. Each dictionary contains the following keys:
            index: the index of the breadcrumb element in the list.
            page: the text of the breadcrumb element.
            url: the URL of the breadcrumb element (if available).
        """
        breadcrumb_list = response.css("nav#breadcrumb span")
        info = []
        index = 0
        for i in breadcrumb_list:
            temp_dict = {}
            text = i.css("a::text").get()
            if text:
                temp_dict["index"] = index
                temp_dict["page"] = text
                link = i.css("a::attr(href)").get()
                if link:
                    temp_dict["url"] = link
                info.append(temp_dict)
                index += 1
        return info

    def extract_lastupdated(self, response) -> str:
        """
        This function extracts the last updated date and time of an article from a given Scrapy response object.
        It returns a string representation of the date and time in ISO 8601 format.
        If the information is not available in the response, it returns None.

        Args:
            response: A Scrapy response object representing the web page from which to extract the information.
        """
        info = response.css("span.time-elapsed")
        if info:
            return info.css("time::attr(datetime)").get()

    def extract_publishd_on(self, response) -> str:
        info = response.css("div.padbtm10")
        info_eng = response.css("div.padtop20")
        # when in some pages containing english text published date is reflected by this variable info_eng
        if info_eng:
            return info_eng.css("time::attr(datetime)").get()
        elif info_eng:
            return info.css("time::attr(datetime)").get()

    def extract_author(self, response) -> list:
        """
        The extract_author function extracts information about the author(s)
        of an article from the given response object and returns it in the form of a list of dictionaries.

        Parameters:
            response (scrapy.http.Response): The response object containing the HTML of the article page.

        Returns:
            A list of dictionaries, where each dictionary contains information about one author.

        """
        info = response.css("div.author")
        pattern = r"[\r\n\t\"]+"
        data = []
        if info:
            for i in info:
                temp_dict = {}
                temp_dict["@type"] = "Person"
                temp_dict["name"] = re.sub(
                    pattern, "", i.css("div a span::text").get()
                ).strip()
                temp_dict["url"] = i.css("div a::attr(href)").get()
                data.append(temp_dict)
            return data

    def extract_thumnail(self, response) -> list:
        """
        The function extract_thumbnail extracts information about the thumbnail image(s) associated with a webpage,
        including its link, width, and height, and returns the information as a list of dictionaries.

        Returns:
            A list of dictionaries, with each dictionary containing information about an image. If no images are found, an empty list is returned.
        """
        info = response.css("div.gallery-item")
        mod_info = response.css(".storypicture img.width100")
        data = []
        if info:
            for i in info:
                image = i.css("div.gallery-item-img-wrapper img::attr(src)").get()
                if image:
                    data.append(image)
        elif mod_info:
            for i in mod_info:
                image = i.css("img::attr(src)").get()
                if image:
                    data.append(image)
        return data

    def extract_video(self, response) -> list:
        """
        A list of video objects containing information about the videos on the webpage.
        """
        info = response.css("div.videoWrapper")
        data = []
        if info:
            for i in info:
                js = i.css("script").get()
                request_link = re.findall(r"playlist\s*:\s*'(\S+)'", js)[0]
                response = requests.get(request_link)
                link = response.json().get("playlist")[0].get("sources")[1].get("file")
                temp_dict = {"link": link}
                data.append(temp_dict)
        return data

    def extract_publisher(self, response) -> list:
        """
        Extracts publisher information from the given response object and returns it as a dictionary.

        Returns:
        - A dictionary containing information about the publisher. The dictionary has the following keys:
            - "@id": The unique identifier for the publisher.
            - "@type": The type of publisher (in this case, always "NewsMediaOrganization").
            - "name": The name of the publisher.
        """
        logo = response.css('link[rel="icon"]::attr(href)').getall()[2]
        img_response = requests.get(logo)
        width, height = Image.open(BytesIO(img_response.content)).size
        a_dict = {
            "@id": "bharat.republicworld.com",
            "@type": "NewsMediaOrganization",
            "name": "Bharat republic word",
            "logo": {
                "@type": "ImageObject",
                "url": logo,
                "width": {"@type": "Distance", "name": str(width) + " px"},
                "height": {"@type": "Distance", "name": str(height) + " px"},
            },
        }
        return [a_dict]

    def extract_all_images(self, response) -> list:
        """
        Extracts all the images present in the web page.

        Returns:
        list: A list of dictionaries containing information about each image,
        such as image link.
        """
        info = response.css("div.embedpicture")
        data = []
        if info:
            for i in info:
                temp_dict = {}
                image = i.css("div.embedimgblock img::attr(src)").get()
                if image:
                    temp_dict["link"] = image
                data.append(temp_dict)
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
            file_name = f"{self.name}-{'sitemap'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.sitemap_data, f, indent=4, default=str)

        if self.type == 'article':
            file_name = f"{self.name}-{'article'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.article_json_data, f, indent=4)
