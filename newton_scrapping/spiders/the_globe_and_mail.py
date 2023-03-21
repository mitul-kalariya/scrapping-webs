"""Spider to scrap Globe and Mail online (EN) news website"""

import os
import json
import logging
from datetime import timedelta, datetime

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
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


class TheGlobeAndMailSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of Globe and Mail online (EN) site"""

    name = "the_globe_and_mail"
    start_urls = ["http://www.theglobeandmail.com/"]
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(TheGlobeAndMailSpider, self).__init__(*args, **kwargs)
        try:
            self.start_urls = []
            self.articles = []
            self.date_range_lst = []
            self.error_msg_dict = {}
            self.article_url = url
            self.scrape_start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.scrape_end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )
            self.type = type

            if self.type == "sitemap":
                self.start_urls.append(
                    "https://www.theglobeandmail.com/web-sitemap.xml"
                )
                if self.scrape_start_date and self.scrape_end_date:
                    if self.scrape_start_date > self.scrape_end_date:
                        raise ValueError("Please enter valid date range.")
                    elif int((self.scrape_end_date - self.scrape_start_date).days) > 30:
                        raise ValueError("Please enter date range between 30 days")
                elif self.scrape_start_date or self.scrape_end_date:
                    raise ValueError(
                        "Invalid argument. Both start_date and end_date argument is required."
                    )
                elif self.article_url:
                    raise ValueError(
                        "Invalid argument. url is not required for sitemap."
                    )
                else:
                    self.scrape_start_date = (
                        self.scrape_end_date
                    ) = datetime.now().date()

                for single_date in self.date_range(
                    self.scrape_start_date, self.scrape_end_date
                ):
                    self.date_range_lst.append(single_date)

            elif self.type == "article":
                self.start_urls.append("https://www.theglobeandmail.com/")
                if not self.article_url:
                    raise ValueError("Argument url is required for type article.")
                if self.scrape_start_date or self.scrape_end_date:
                    raise ValueError(
                        "Invalid argument. start_date and end_date argument is not required for article."
                    )
            else:
                raise ValueError(
                    "Invalid type argument. Must be 'sitemap' or 'article'."
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

    def date_range(self, start_date, end_date):
        """
        return range of all date between given date
        if not end_date then take start_date as end date
        """
        try:
            for n in range(int((end_date - start_date).days) + 1):
                yield start_date + timedelta(n)
        except Exception as exception:
            self.log(
                "Error occured while generating date range. " + str(exception),
                level=logging.ERROR,
            )

    def parse(self, response):
        """
        differentiate sitemap and article and redirect its callback to different parser
        """
        if self.error_msg_dict:
            raise CloseSpider(self.error_msg_dict.get("error_msg"))
        self.logger.info("Parse function called on %s", response.url)
        if "web-sitemap.xml" in response.url:
            for url, date in zip(
                Selector(response, type="xml")
                .xpath("//sitemap:loc/text()", namespaces=self.namespace)
                .getall(),
                Selector(response, type="xml")
                .xpath("//sitemap:lastmod/text()", namespaces=self.namespace)
                .getall(),
            ):
                try:
                    date_datetime = datetime.strptime(date.strip()[:10], "%Y-%m-%d")
                    if self.date_in_date_range(date_datetime):
                        yield scrapy.Request(
                            url.strip(), callback=self.parse_sitemap_article
                        )
                except Exception as exception:
                    breakpoint()
                    self.log(
                        "Error occured while scrapping urls from given sitemap url. "
                        + str(exception),
                        level=logging.ERROR,
                    )
        else:
            yield scrapy.Request(self.article_url, callback=self.parse_article)

    def parse_sitemap_article(self, response):
        """
        parse sitemap article and  scrap title and link
        """
        try:
            title = response.css("h1.c-primary-title::text").get()
            if title:
                article = {"link": response.url, "title": title}
                self.articles.append(article)
        except Exception as exception:
            self.log(
                "Error occured while scraping sitemap's article. " + str(exception),
                level=logging.ERROR,
            )

    def date_in_date_range(self, published_date):
        """
        return true if date is in given start date and end date range
        """
        try:
            if published_date.date() in self.date_range_lst:
                return True
            else:
                return False
        except Exception as exception:
            self.log(
                "Error occured while checking date in given date range. "
                + str(exception),
                level=logging.ERROR,
            )

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        """
        try:
            json_ld_blocks = []
            blocks = response.css('script[type="application/ld+json"]::text').getall()
            for block in blocks:
                json_ld_blocks.append(json.loads(block))
            author_name = json_ld_blocks[0].get("author")
            author_type = json_ld_blocks[0].get("@type")
            description = json_ld_blocks[0].get("description")
            modified_at = json_ld_blocks[0].get("dateModified")
            published_at = json_ld_blocks[0].get("datePublished")
            publisher_id = json_ld_blocks[0].get("publisher").get("@id")
            publisher_type = json_ld_blocks[0].get("publisher").get("@type")
            publisher_name = json_ld_blocks[0].get("publisher").get("name")
            logo_type = json_ld_blocks[0].get("publisher").get("logo").get("@type")
            logo_url = json_ld_blocks[0].get("publisher").get("logo").get("url")
            logo_width = json_ld_blocks[0].get("publisher").get("logo").get("width")
            logo_height = json_ld_blocks[0].get("publisher").get("logo").get("height")
            title = json_ld_blocks[0].get("headline")
            text = response.css("p.c-article-body__text::text").getall()
            image_url = json_ld_blocks[0].get("image", {}).get("url")
            image_caption = json_ld_blocks[0].get("image", {}).get("description")
            content_type = response.headers.get("Content-Type").decode("utf-8")

            article = {
                "raw_response": {
                    "content_type": content_type,
                    "content": response.text,
                },
                "parsed_json": {
                    "main": json_ld_blocks,
                },
                "parsed_data": {
                    "author": [{"@type": author_type, "name": author_name}],
                    "description": [description],
                    "published_at": [published_at],
                    "modified_at": [modified_at],
                    # "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                    "publisher": [
                        {
                            "@id": publisher_id,
                            "@type": publisher_type,
                            "name": publisher_name,
                            "logo": {
                                "type": logo_type,
                                "url": logo_url,
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
                    "text": text,
                    "title": [title],
                    "images": [{"link": image_url, "caption": image_caption}],
                    },
                }
            if not (image_url and image_caption):
                article["parsed_data"].pop("images")
            self.articles.append(article)

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
                with open(f"{folder_structure}/{filename}.json", "w") as file:
                    json.dump(self.articles, file, indent=4)
        except Exception as exception:
            self.log(
                "Error occured while writing json file" + str(exception),
                level=logging.ERROR,
            )


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(TheGlobeAndMailSpider, type="sitemap")
    process.start()
