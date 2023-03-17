"""Spider to scrap Suddeutsche news website"""

import itertools
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


class SueddeutscheSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of Suddeutsche site"""

    name = "sueddeutsche"
    start_urls = ["http://www.sueddeutsche.de/"]
    
    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(SueddeutscheSpider, self).__init__(*args, **kwargs)
        try:
            self.start_urls = []
            self.articles = []
            self.date_range_lst = []
            self.error_msg_dict = {}
            self.article_url = url
            self.error_msg_dict = {}
            self.scrape_start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.scrape_end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )
            self.type = type

            if self.type == "sitemap":
                self.start_urls.append("https://www.sueddeutsche.de/archiv")
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
                if not self.article_url:
                    raise ValueError("Argument url is required for type article.")
                if self.scrape_start_date or self.scrape_end_date:
                    raise ValueError(
                        "Invalid argument.start_date and end_date argument is not required for article."
                    )
                self.start_urls.append(url)
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
            for date in range(int((end_date - start_date).days) + 1):
                yield start_date + timedelta(date)
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
        if "archiv" in response.url:
            categories = response.css(".department-overview-title a::attr(href)").getall()
            for category in categories:
                for single_date in self.date_range(self.scrape_start_date, self.scrape_end_date):
                    try:
                        self.logger.debug("Parse function called on %s", response.url)
                        yield scrapy.Request(
                            f"https://www.sueddeutsche.de{category}/{single_date.year}/{single_date.month}",
                            callback=self.parse_sitemap,
                            meta={'date':single_date}
                        )
                    except Exception as exception:
                        self.log(
                            "Error occured while iterating sitemap url. " + str(exception),
                            level=logging.ERROR,
                        )
        else:
            yield self.parse_article(response)



    def parse_sitemap(self, response):
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        """
        try:
            for date,link in zip(
                response.css(".entrylist__time::text").getall(),
                response.css(".entrylist__content a::attr(href)").getall(),
            ):
                if len(date) > 18:
                    date_datetime = datetime.strptime(date.strip(), "%d.%m.%Y | %H:%M")
                else:
                    date_datetime = datetime.now()
                if self.date_in_date_range(date_datetime):
                    yield scrapy.Request(link, callback=self.parse_sitemap_article)
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
            title = response.css("h2 > span.css-1bhnxuf::text").get()
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

            parsed_json_context = json_ld_blocks[0].get('@context')
            parsed_json_type = json_ld_blocks[0].get('@type')
            articles_category = json_ld_blocks[0].get('articleSection')
            published_date = json_ld_blocks[0].get('datePublished')
            modified_date = json_ld_blocks[0].get('dateModified')
            content_type = response.headers.get("Content-Type").decode("utf-8")
            images = response.css('.css-1b63ry7::attr(src)').getall()
            caption = response.css('.css-cd29nr::text').getall()
            text = response.css('.css-13wylk3::text').getall()
            headline = json_ld_blocks[0].get('headline')
            publisher_type = json_ld_blocks[0].get('publisher').get('@type')
            publisher_name = json_ld_blocks[0].get('publisher').get('name')
            logo_url = json_ld_blocks[0].get('publisher').get('logo').get('url')
            logo_type = json_ld_blocks[0].get('publisher').get('logo').get('@type')
            logo_width = json_ld_blocks[0].get('publisher').get('logo').get('width')
            logo_height = json_ld_blocks[0].get('publisher').get('logo').get('height')
            author_name = json_ld_blocks[0].get('author')[0].get('name')
            author_type = json_ld_blocks[0].get('author')[0].get('@type')
            alternativeHeadline = json_ld_blocks[0].get('description')
            description = json_ld_blocks[0].get('description')
            publisher_id = response.css('.custom-l20qco::attr(href)').get()

            article = {
                "raw_response": {
                    "content_type": content_type,
                    "content": response.text,
                },
                "parsed_json": {
                    "main": {
                        "@context": parsed_json_context,
                        "@type": parsed_json_type,
                        "mainEntityOfPage": {"@type": "WebPage", "@id": response.url},
                        "headlines": headline,
                        "alternativeHeadline": alternativeHeadline,
                        "datepublished": published_date,
                        "datemodified": modified_date,
                        "description": description,
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
                    },
                    "misc": json_ld_blocks
                },
                "parsed_data": {
                    "author": [
                        {
                            "@type": author_type,
                            "name": author_name
                        }
                    ],
                    "description": [description],
                    "published_at": [published_date],
                    "modified_at": [modified_date],
                    # "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                    "publisher": [
                        {
                            "@id": publisher_id,
                            "@type": publisher_type,
                            "name": publisher_name,
                            "logo": {
                                "type": "ImageObject",
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
                    "title": [headline],
                    "images": [
                        {"link": img, "caption": cap}
                        for img, cap in itertools.zip_longest(
                            images, caption, fillvalue=None
                        )
                    ],
                    "section": [articles_category],
                },
            }
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
                if self.type == "sitemap":
                    filename = f'{self.name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
                elif self.type == "article":
                    filename = f'{self.name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
                with open(f"{filename}.json", "w") as file:
                    json.dump(self.articles, file, indent=4)
        except Exception as exception:
            self.log(
                "Error occured while writing json file" + str(exception),
                level=logging.ERROR,
            )


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(SueddeutscheSpider, type="sitemap")
    process.start()
