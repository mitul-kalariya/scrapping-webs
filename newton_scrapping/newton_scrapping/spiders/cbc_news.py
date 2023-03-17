"""Spider to scrap CBC news website"""

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


class CbcNewsSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of CBC News site"""

    name = "cbc_news"
    start_urls = ["http://www.cbc.ca/"]

    def __init__(
        self, *args, type=None, url=None, start_date=None, end_date=None, **kwargs
    ):
        """init method to take date, type and validating it"""

        super(CbcNewsSpider, self).__init__(*args, **kwargs)
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
                self.start_urls.append("https://www.cbc.ca/rss/")
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
        if "rss" in response.url:
            for link in response.css('td.content a::attr(href)').getall():
                try:
                    yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap,
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
        for url, date in zip(
            Selector(response, type="xml").xpath("//item/link/text()").getall(),
            Selector(response, type="xml").xpath("//item/pubDate/text()").getall()
        ):
            try:
                date_datetime = datetime.strptime(date[:-3].strip(), '%a, %d %b %Y %H:%M:%S')
                if self.date_in_date_range(date_datetime):
                    yield scrapy.Request(
                        url.strip(), callback=self.parse_sitemap_article
                    )
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
            title = response.css("h1.detailHeadline::text").get()
            if title:
                article = {"link": response.url.replace("?cmp=rss",""), "title": title}
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
            thumbnail_url = []
            video_caption = ""
            video_url = ""
            description = ""
            alternativeheadline = ""
            parsed_json_context = ""
            headline = ""
            articles_category = ""
            author_url = ""
            author_name = ""
            author_type = ""
            publisher_id = ""
            publisher_type = ""
            blocks = response.css('script[type="application/ld+json"]::text').getall()
            for block in blocks:
                if json.loads(block).get('dateModified'):
                    modified_date = json.loads(block).get('dateModified', None)
                if json.loads(block).get('video', None):
                    video_caption = json.loads(block).get('video', None)[0].get('alternativeHeadline', None)
                if json.loads(block).get('thumbnailUrl'):
                    thumbnail_url = json.loads(block).get('thumbnailUrl')
                if json.loads(block).get('alternateName'):
                    description = json.loads(block).get('alternateName', None)
                    alternativeheadline = json.loads(block).get('alternateName', None)
                if json.loads(block).get('@context'):
                    parsed_json_context = json.loads(block).get('@context', None)
                if json.loads(block).get('headline'):
                    headline = json.loads(block).get('headline', None)
                if json.loads(block).get('articleSection'):
                    articles_category = json.loads(block).get('articleSection', None)
                if json.loads(block).get('author'):
                    if json.loads(block).get('author', None)[0].get('image', None):
                        author_url = json.loads(block).get('author', None)[0].get('image', None).get('url', None)
                    author_name = json.loads(block).get('author', None)[0].get('name', None)
                    author_type = json.loads(block).get('author', None)[0].get('@type', None)
                    if json.loads(block).get('author', None)[0].get('contactPoint', None):
                        publisher_id = json.loads(block).get('author', None)[0].get('contactPoint', None).get('url', None).split('/news')[0]
                if json.loads(block).get('video', None):
                    video_url = json.loads(block).get('video', None)[0].get('contentUrl', None)
                if json.loads(block).get('publisher', None):
                    publisher_type = json.loads(block).get('publisher', None).get('@type', None)
                json_ld_blocks.append(json.loads(block))
            content_type = response.headers.get("Content-Type").decode("utf-8")
            published_date = response.css('.timeStamp::text').get().split('|')[0]

            publisher_name = response.css('head > title::text').get().split('|')[1]
            image_url = response.css('.storyWrapper .placeholder img::attr(src)').getall()
            image_caption = [i.strip() for i in response.css('figcaption::text').getall() if i.strip()]
            image_caption = [i + j for i, j in zip(image_caption[::2], image_caption[1::2])]
            text = response.css('.story p::text').getall()

            article = {
                "raw_response": {
                    "content_type": content_type,
                    "content": response.text,
                },
                "parsed_json": {
                    "main": {
                        "@context": parsed_json_context,
                        "@type": "NewsArticle",
                        "mainEntityOfPage": {"@type": "WebPage", "@id": response.url},
                        "headlines": headline,
                        "alternativeheadlines": alternativeheadline,
                        "datemodified": modified_date,
                        "datepublished": published_date,
                        "publisher": [
                            {

                                "@id": publisher_id,
                                "@type": publisher_type,
                                "name": publisher_name,

                            }
                        ]
                    },
                    "misc": json_ld_blocks,
                },
                "parsed_data": {
                    "author": [
                        {"@type": author_type, "name": author_name, "url": author_url}
                    ],
                    "description": description,
                    "modified_at": modified_date,
                    "published_at": published_date,
                    # "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                    "publisher": [
                        {

                            "@id": publisher_id,
                            "@type": publisher_type,
                            "name": publisher_name,
                        }
                    ],
                    "text": text,
                    "thumbnail_image": [thumbnail_url],
                    "title": [headline],
                    "images": [
                        {"link": img, "caption": cap}
                        for img, cap in itertools.zip_longest(
                            image_url, image_caption, fillvalue=None
                        )
                    ],
                    "video": {"link": video_url, "caption": video_caption},
                    "section": articles_category,
                },
            }
            if not video_url:
                article.get('parsed_data').pop('video')
            if not image_url:
                article.get('parsed_data').pop('images')
            self.articles.append(article)
        except ValueError as exception:
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
    process.crawl(CbcNewsSpider, type="sitemap")
    process.start()
