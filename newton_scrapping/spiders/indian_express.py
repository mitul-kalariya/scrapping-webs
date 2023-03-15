"""Spider to scrap Indian Express news website"""

import logging
import scrapy
import json
import itertools
from datetime import date, timedelta, datetime
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider


# Setting the threshold of logger to DEBUG
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(name)s] %(levelname)s:   %(message)s',
                    filename="logs.log",
                    filemode='a',
                    datefmt='%Y-%m-%d %H:%M:%S')
# Creating an object
logger = logging.getLogger()


class IndianexpressSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of Indian Express site"""

    name = "indian_express"
    start_urls = ['https://indianexpress.com/']
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


    def __init__(self, type=None, url=None, start_date=None, end_date=None, *args, **kwargs):
        """init method to take date, type and validating it"""

        super(IndianexpressSpider, self).__init__(*args, **kwargs)
        try:
            self.start_urls = []
            self.articles = []
            self.date_range_lst = []
            self.article_url = url
            self.scrape_start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            self.scrape_end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            self.type = type
            self.error_msg_dict = {}

            if self.type == "sitemap":
                self.start_urls.append("https://indianexpress.com/sitemap.xml")
                if self.scrape_start_date and self.scrape_end_date:
                    if self.scrape_start_date > self.scrape_end_date:
                        raise ValueError("Please enter valid date range.")
                    elif int((self.scrape_end_date-self.scrape_start_date).days) > 30:
                        raise ValueError("Please enter date range between 30 days")
                elif self.scrape_start_date or self.scrape_end_date:
                    raise ValueError("Invalid argument. Both start_date and end_date argument is required.")
                elif self.article_url:
                    raise ValueError("Invalid argument. url is not required for sitemap.")
                else:
                    self.scrape_start_date = self.scrape_end_date = datetime.now().date()

                for single_date in self.date_range(self.scrape_start_date, self.scrape_end_date):
                    self.date_range_lst.append(single_date)
            
            elif self.type == "article":
                if not self.article_url:
                    raise ValueError("Argument url is required for type article.")
                if self.scrape_start_date or self.scrape_end_date:
                    raise ValueError("Invalid argument. start_date and end_date argument is not required for article.")
                self.start_urls.append(url)
            else:
                raise ValueError("Invalid type argument. Must be 'sitemap' or 'article'.")
        except Exception as exception:
            self.error_msg_dict["error_msg"] = "Error occured while taking type, url, start_date and end_date args. " + str(exception)
            self.log("Error occured while taking type, url, start_date and end_date args. " + str(exception), level=logging.ERROR)



    def date_range(self, start_date, end_date):
        """
        return range of all date between given date
        if not end_date then take start_date as end date
        """
        try:
            for n in range(int((end_date - start_date).days) + 1):
                yield start_date + timedelta(n)
        except Exception as exception:
            self.log("Error occured while generating date range. " + str(exception), level=logging.ERROR)
            
    def parse(self, response):
        """
        differentiate sitemap and article and redirect its callback to different parser
        """
        if self.error_msg_dict:
            raise CloseSpider(self.error_msg_dict.get("error_msg"))
        self.logger.info('Parse function called on %s', response.url)
        if "sitemap.xml" in response.url:
            for single_date in self.date_range(self.scrape_start_date, self.scrape_end_date):
                try:
                    self.logger.debug('Parse function called on %s', response.url)
                    # url info : https://indianexpress.com/sitemap.xml?yyyy=2023&mm=03&dd=10
                    yield scrapy.Request(
                        f"https://indianexpress.com/sitemap.xml?yyyy={single_date.year}&mm={single_date.month}&dd={single_date.day}",
                        callback=self.parse_sitemap)
                except Exception as exception:
                    self.log("Error occured while iterating sitemap url. " + str(exception), level=logging.ERROR)
        else:
            yield self.parse_article(response)

    def parse_sitemap(self, response):
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        """
        try:
            for article_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                    namespaces=self.namespace).getall():
                yield scrapy.Request(article_url, callback=self.parse_sitemap_article)
        except Exception as exception:
            self.log("Error occured while scrapping urls from given sitemap url. " + str(exception), level=logging.ERROR)

    def parse_sitemap_article(self, response):
        """
        parse sitemap article and  scrap title and link
        """
        try:
            title = response.css("h1.native_story_title::text").get()
            if title:
                article = {
                    "link": response.url,
                    "title": title
                }
                self.articles.append(article)
        except Exception as exception:
            self.log("Error occured while scraping sitemap's article. " + str(exception), level=logging.ERROR)

    def date_in_date_range(self,published_date):
        """
        return true if date is in given start date and end date range
        """
        try:
            if published_date.date() in self.date_range_lst:
                return True
            else:
                return False
        except Exception as exception:
            self.log("Error occured while checking date in given date range. " + str(exception), level=logging.ERROR)

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        """
        try:
            published_date = response.css('div.ie-first-publish span::text').getall()
            modified_date = response.css('div.editor-date-logo div span::text').getall() or response.css('span.updated-date::attr(content)').getall()
            if not modified_date:
                modified_date = None
            articles_category = response.css('ol.m-breadcrumb li a::text').getall()
            content_type = response.headers.get("Content-Type").decode("utf-8")
            description = response.css('h2.synopsis::text').getall()
            language = response.css('html::attr(lang)').getall()
            city = response.css('div.editor-date-logo div::text').getall()
            text = response.css('div#pcl-full-content p::text').getall()
            images = response.css('span.custom-caption > img::attr(src)').getall()
            caption1 = response.css('span.ie-custom-caption::text').getall()
            caption2 = response.css('span.custom-caption::text').getall()
            caption = caption1 + caption2
            tags = response.css('div.storytags ul li a::text').getall()
            headline = response.css('div.heading-part  h1::text').getall()
            alternativeheadline = response.css('h2.synopsis::text').getall()
            author_name = response.css('div.editor div a::text').getall()
            author_url = response.css('div.editor div a::attr(href)').getall()
            social_url = response.css('ul.g-follow a::attr(href)').getall()
            social_name = response.css('ul.g-follow a::attr(title)').getall()
            logo_url = response.css("#wrapper div.main-header__logo img::attr(src)").get()
            logo_height = response.css("#wrapper div.main-header__logo img::attr(height)").get()
            logo_width = response.css("#wrapper div.main-header__logo img::attr(width)").get()
            copyright = response.css("div.g-footer-aux div.privacy::text").getall()
            publisher_name = response.css("#wrapper div.main-header__logo img::attr(title)").getall()
            video_url = response.css("span.embed-youtube iframe::attr(src)").getall()

            json_ld_blocks = []
            blocks = response.css('script[type="application/ld+json"]::text').getall()

            for block in blocks:

                if json.loads(block).get('author'):
                    author_type = json.loads(block).get('author')[0].get('@type')

                if json.loads(block).get('publisher'):
                    publisher_type = json.loads(block).get('publisher').get('@type')
                if json.loads(block).get('address'):
                    country = json.loads(block).get('address').get('addressRegion')
                json_ld_blocks.append(json.loads(block))


            article = {
                "raw_response": {
                    "content_type": content_type,
                    "content": response.text,
                    "language": language,
                    "country": country,
                    "city": city
                },
                "parsed_json": {
                    "main": {
                        "@type": "NewsArticle",
                        "mainEntityOfPage": {
                            "@type": "WebPage",
                            "@id": response.url
                        },
                        "headlines": headline,
                        "alternativeheadlines": alternativeheadline,
                        "datemodified": modified_date,
                        "datepublished": published_date,
                        "publisher": [
                            {
                                "@id": "",
                                "@type": "NewsMediaOrganization",
                                "name": publisher_name,
                                "logo": {
                                    "type": "ImageObject",
                                    "url": logo_url,
                                    "width": {"type": "Distance", "name": f"{logo_width} px"},
                                    "height": {"type": "Distance", "name": f"{logo_height} px"},
                                },
                            }
                        ],
                        "socialLinks": [
                            {
                                "deprecated": True,
                                "deprecation_msg": "Please use social_links.",
                                "site": social_name,
                                "url": social_url
                            },
                        ],
                        "copyright": copyright
                    },
                    "misc": json_ld_blocks
                },
                "parsed_data": {
                    "author": [
                        {
                            "@type": author_type,
                            "name": author_name,
                            "url": author_url
                        }
                    ],
                    "description": description,
                    "modified_at": modified_date,
                    "published_at": published_date,
                    "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                    "publisher": [
                        {
                            "@id": "www.indianexpress.com",
                            "@type": publisher_type,
                            "name": publisher_name,
                            "logo": {
                                "type": "ImageObject",
                                "url": logo_url,
                                "width": {"type": "Distance", "name": f"{logo_width} px"},
                                "height": {"type": "Distance", "name": f"{logo_height} px"},
                            },
                        }
                    ],
                    "text": text,
                    "title": headline,
                    "images": [
                        {
                            "link": img,
                            "caption": cap
                        } for img, cap in itertools.zip_longest(images, caption, fillvalue=None)
                    ]
                    ,
                    "video": {"link": video_url},
                    "section": articles_category,
                    "tags": tags
                }
            }
            self.articles.append(article)
        except Exception as exception:
            self.log("Error occured while scrapping an article for this link {response.url}." + str(exception), level=logging.ERROR)

    def closed(self, response):
        """
        store all scrapped data into json file with given date in filename
        """
        try:
            if not self.articles:
                self.log("No articles or sitemap url scapped.", level=logging.INFO)
            else:
                if self.type == "sitemap":
                    filename = f'{self.name}-sitemap-{self.scrape_start_date.strftime("%Y-%m-%d_%H-%M-%S")}{" - " + self.scrape_end_date.strftime("%Y-%m-%d_%H-%M-%S") if self.scrape_end_date != self.scrape_start_date else ""}.json'
                elif self.type == "article":
                    filename = f'{self.name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
                with open(f'{filename}.json', 'w') as f:
                    json.dump(self.articles, f, indent=4)
        except Exception as exception:
            self.log("Error occured while writing json file" + str(exception), level=logging.ERROR)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(IndianexpressSpider, type="sitemap")
    process.start()
