"""Spider to scrap Indian Express news website"""

import logging
import scrapy
import json
import  itertools
from datetime import date, timedelta, datetime
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings


logging.basicConfig(level=logging.DEBUG,
# Setting the threshold of logger to DEBUG
                    format='%(asctime)s [%(name)s] %(levelname)s:   %(message)s',
                    filename="logs.log",
                    filemode='a',
                    datefmt='%Y-%m-%d %H:%M:%S')
# Creating an object
logger = logging.getLogger()


class IndianexpressSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of Indian Express site"""

    name = 'indianexpress'
    start_urls = ['https://indianexpress.com/']

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    def __init__(self, category=None, start_date=None, end_date=None, *args, **kwargs):
        """init method to take date, category and validating it"""

        super(IndianexpressSpider, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.date_range_lst = []
        self.scrape_start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        self.scrape_end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        self.category = category

        if self.category == "sitemap":
            self.start_urls.append("https://indianexpress.com/sitemap.xml")
        elif self.category == "articles":
            self.start_urls.append("https://indianexpress.com/")
        else:
            raise ValueError("Invalid category argument. Must be 'sitemap' or 'articles'.")

        if self.scrape_end_date and self.scrape_start_date > self.scrape_end_date:
            raise ValueError("Please enter valid date range.")

        if self.scrape_start_date and self.category == "articles":
            for single_date in self.date_range(self.scrape_start_date, self.scrape_end_date):
                self.date_range_lst.append(single_date)

    def date_range(self, start_date, end_date=None):
        """
        return range of all date between given date
        if not end_date then take start_date as end date
        """
        if not end_date:
            end_date = start_date
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(n)
            
    def parse(self, response):
        """
        differentiate sitemap and articles and redirect its callback to different parser
        """
        self.logger.info('Parse function called on %s', response.url)
        if "sitemap.xml" in response.url:
            if self.scrape_start_date:
                for single_date in self.date_range(self.scrape_start_date, self.scrape_end_date):
                    self.logger.debug('Parse function called on %s', response.url)
                    print("Scraping articles from date: {}".format(self.scrape_start_date))
                    # https://indianexpress.com/sitemap.xml?yyyy=2023&mm=03&dd=10
                    yield scrapy.Request(
                        f"https://indianexpress.com/sitemap.xml?yyyy={single_date.year}&mm={single_date.month}&dd={single_date.day}",
                        callback=self.parse_sitemap)
            else:
                for url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                namespaces=self.namespace).getall()[0:2]:
                    yield scrapy.Request(url, callback=self.parse_sitemap)
        else:
            article1 = response.css('div.lead-stories a::attr(href)').getall()
            article2 = response.css('div.section-common a::attr(href)').getall()
            thumbnail1 = response.css('div.lead-stories a img::attr(src)').getall()
            thumbnail2 = response.css('div.section-common a img::attr(src)').getall()
            thumbnail_images = thumbnail1 + thumbnail2
            article_links = article1 + article2
            for index, link in enumerate(article_links):
                if "https://indianexpress.com/section" in link:
                    pass
                elif "https://indianexpress.com/" in link:
                    yield scrapy.Request(link, callback=self.parse_article)

    def parse_sitemap(self, response):
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        """
        for article_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                namespaces=self.namespace).getall():
            yield scrapy.Request(article_url, callback=self.parse_sitemap_article)

    def parse_sitemap_article(self, response):
        """
        parse sitemap articles and  scrap title and link
        """
        title = response.css("h1.native_story_title::text").get()
        if title:
            article = {
                "link": response.url,
                "title": title
            }
            self.articles.append(article)

    def date_in_date_range(self,published_date):
        """
        return true if date is in given start date and end date range
        """
        if not self.date_range_lst:
            return True
        if published_date.date() in self.date_range_lst:
            return True
        else:
            return False

    def parse_article(self, response):
        """
        parse article and append related data to class's articles variable
        """
        published_date = response.css('div.ie-first-publish span::text').getall()
        try:
            modified_date = response.css('div.editor-date-logo div span::text').getall() or response.css('span.updated-date::attr(content)').getall()
            # response.css('span.updated-date::attr(content)').getall()
        except:
            modified_date = None
        if modified_date:
            date_to_check = datetime.strptime(modified_date[0].replace("Updated:", "").strip(), '%B %d, %Y %H:%M IST')
        elif not published_date:
            return
        else:
            date_to_check = datetime.strptime(published_date[0].strip(), '%d-%m-%Y at %H:%M IST')
        if not self.date_in_date_range(date_to_check):
            return
        articles_category = response.css('ol.m-breadcrumb li a::text').getall()
        # articles_category = response.css('div.m-breadcrumb li a::text').getall()
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


        article = {
            "raw_response": {
                "content_type": content_type,
                "content": response.text,
                "language": language,
                "country": "India",
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
                }
            },
            "parsed_data": {
                "author": [
                    {
                        "@type": "Person",
                        "name": author_name,
                        "url" :author_url
                    }
                ],
                "description": description,
                "modified_at": modified_date,
                "published_at": published_date,
                "time_scraped": [datetime.today().strftime("%Y-%m-%d")],
                "publisher": [
                    {
                        "@id": "www.indianexpress.com",
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
                "text": text,
                "thumbnail_image": [None],
                "title": headline,
                "images": [
                    {
                        "link": img,
                        "caption": cap
                    } for img, cap in itertools.zip_longest(images, caption, fillvalue=None)
                ]
                ,
                "video": {"link": video_url, "caption": None},
                "section": articles_category,
                "tags": tags
            }
        }
        self.articles.append(article)

    def closed(self, response):
        """
        store all scrapped data into json file with given date in filename
        """
        if self.category == "sitemap":
            filename = f'indianexpress-sitemap-{self.scrape_start_date.strftime("%Y-%m-%d") if self.scrape_start_date else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}{" - " + self.scrape_end_date.strftime("%Y-%m-%d") if self.scrape_end_date else ""}.json'
        elif self.category == "articles":
            filename = f'indianexpress-articles-{self.scrape_start_date.strftime("%Y-%m-%d") if self.scrape_start_date else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}{" - " + self.scrape_end_date.strftime("%Y-%m-%d") if self.scrape_end_date else ""}.json'
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(IndianexpressSpider, category="articles")
    process.start()
