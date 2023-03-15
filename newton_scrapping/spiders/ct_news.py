"""Scrapy spider for CTV News site"""

import re
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


class CtvnewsSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of CTV news site"""
    space_remover_pattern = r'[\n|\r|\t]+'
    name = "ct_news"
    start_urls = ["http://www.ctvnews.ca/"]
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    namespace_news = {"sitemap": "http://www.google.com/schemas/sitemap-news/0.9"}


    def __init__(self, type=None, url=None, start_date=None, end_date=None, *args, **kwargs):
        """init method to take date, type and validating it"""

        super(CtvnewsSpider, self).__init__(*args, **kwargs)
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
                self.start_urls.append("https://www.ctvnews.ca/sitemap_news.xml")
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
                self.start_urls.append(self.article_url)
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
        if "sitemap_news.xml" in response.url:
            for link, date in zip(Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall(), Selector(response, type='xml').xpath('//sitemap:publication_date/text()', namespaces=self.namespace_news).getall()):
                try:
                    date_datetime_obj = datetime.strptime(date.strip()[:-6],"%Y-%m-%dT%H:%M:%S")
                    if self.date_in_date_range(date_datetime_obj):
                        yield scrapy.Request(link.strip(), callback=self.parse_sitemap_article)
                except Exception as exception:
                    self.log("Error occured while iterating sitemap url. " + str(exception), level=logging.ERROR)

        else:
            yield self.parse_article(response)

    def parse_sitemap_article(self, response):
        """
        parse sitemap article and  scrap title and link
        """
        try:
            title = response.css("h1.c-title__text::text").get()
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
            content_type = response.headers.get("Content-Type").decode("utf-8")
            language = response.css('html::attr(lang)').getall()
            imageurl = response.css('.inline-image::attr(src)').getall()
            image = None
            for img in imageurl:
                if "https://www.ctvnews.ca/" in img:
                    image = img
                else:
                    image = "https://www.ctvnews.ca/" + img

            caption = response.css('.c-text span::text').getall()
            text = response.css('.twitter-tweet::text, .c-text p::text').getall()
            copyright = response.css('.c-quickArticle__footer__copyright::text').getall()
            if copyright:
                copyright = copyright[1]
            articles_category = response.css('.c-breadcrumb__item__link span::text').getall()
            logo_urls = response.css('.c-quickArticle__header_logo::attr(src)').getall()
            for logo in logo_urls:
                logo_url = "https://www.ctvnews.ca/" + logo

            author = json.loads(response.css("bio-content::attr(content)").get())
            for au in author:
                first_name = au.get('firstName')
                last_name = au.get('lastName')
                full_name = first_name + " " + last_name

            json_ld_blocks = []
            blocks = response.css('script[type="application/ld+json"]::text').getall()
            for block in blocks:
                json_ld_blocks.append(json.loads(re.sub(self.space_remover_pattern,"", block).strip()))

            publisher_name = json_ld_blocks[0].get('publisher', None).get('name', None)
            publisher_type = json_ld_blocks[0].get('publisher', None).get('@type', None)
            published_date = json_ld_blocks[0].get('datePublished', None)
            updated_date = json_ld_blocks[0].get('dateModified',None)
            headline = json_ld_blocks[0].get('headline', None)
            alternativeheadline = json_ld_blocks[0].get('description', None)
            author_url = json_ld_blocks[0].get('author', None)[0].get('sameAs', None)
            author_type = json_ld_blocks[0].get('author', None)[0].get('@type', None)
            thumbnail_url = json_ld_blocks[0].get('thumbnailUrl', None)
            parsed_json_type = json_ld_blocks[0].get('@type', None)
            parsed_json_content =json_ld_blocks[0].get('@context', None)


            article = {
                "raw_response": {
                    "content_type": content_type,
                    "content": response.text,
                    "language": language,
                    "country": "India",
                },
                "parsed_json": {
                    "main": {
                        "@context": parsed_json_content,
                        "@type": parsed_json_type,
                        "mainEntityOfPage": {
                            "@type": "WebPage",
                            "@id": response.url
                        },
                        "headlines": headline,
                        "alternativeheadlines": alternativeheadline,
                        "datemodified": updated_date,
                        "datepublished": published_date,
                        "publisher": [
                            {
                                "@id": "",
                                "@type": publisher_type,
                                "name": publisher_name,
                                "logo": {
                                    "type": "ImageObject",
                                    "url": logo_url,
                                },
                            }
                        ],
                        "copyright": copyright
                    },
                    "misc": json_ld_blocks
                },
                "parsed_data": {
                    "author": [
                        {
                            "@type": author_type,
                            "name": full_name,
                            "url": author_url
                        }
                    ],
                    "description": alternativeheadline,
                    "modified_at": updated_date,
                    "published_at": published_date,
                    "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                    "publisher": [
                        {
                            "@id": "www.ctvnews.ca",
                            "@type": publisher_type,
                            "name": publisher_name,
                            "logo": {
                                "type": "ImageObject",
                                "url": logo_url
                            },
                        }
                    ],
                    "text": text,
                    "thumbnail_image": [thumbnail_url],
                    "title": headline,
                    "images": [
                        {
                            "link": image,
                            "caption": caption
                        }
                    ]
                    ,
                    "video": {"link": None, "caption": None},
                    "section": articles_category,
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
    process.crawl(CtvnewsSpider, type="sitemap")
    process.start()
