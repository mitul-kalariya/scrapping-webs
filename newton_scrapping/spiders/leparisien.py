import scrapy
import json
import os
from datetime import datetime
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings
from .utils import check_cmd_args, get_article_data ,set_article_dict

class LeParisien(scrapy.Spider):
    name = "le_parisien"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': 'http://www.google.com/schemas/sitemap-news/0.9'}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(LeParisien, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.start_date = start_date
        self.end_date = end_date
        self.url = url
        self.today = None
        check_cmd_args(self, self.start_date, self.end_date)

    def parse(self, response):
        if self.type == "sitemap":
            for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                     namespaces=self.namespace).getall():
                yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        elif self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
        """
           Parses the sitemap and extracts the article URLs and their last modified date.
           If the last modified date is within the specified date range, sends a request to the article URL
           :param response: the response from the sitemap request
           :return: scrapy.Request object
        """
        
        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        published_date = Selector(response, type='xml').xpath('//news:publication_date/text()',
                                                              namespaces=self.namespace).getall()
        title = Selector(response, type='xml').xpath('//news:title/text()', namespaces=self.namespace).getall()
        if self.start_date is not None and self.end_date is not None:
            self.logger.info('Fetching sitemap data for given date range  ------------')
            for article, date, title in zip(article_urls, published_date, title):
                if self.start_date <= datetime.strptime(date.split('T')[0], '%Y-%m-%d') <= self.end_date:
                    
                    article = {
                        "link": article,
                        "title": title,
                    }
                    self.articles.append(article)


        elif self.start_date is None and self.end_date is None:
            for article, date, title in zip(article_urls, published_date, title):
                _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                if _date == self.today_date:
                    self.logger.info("Fetching today's sitemap data ------------")
                    article = {
                        "link": article,
                        "title": title,
                    }
                    self.articles.append(article)

        elif self.start_date is None or self.end_date is None:
            raise ValueError("start_date and end_date both required.")
        else:
            raise ValueError("Invalid date range")

    def parse_sitemap_article(self, response):
        """
        Parse article information from a given sitemap URL.

        :param response: HTTP response from the sitemap URL.
        :return: None
        """

        title = response.css('#top > header > h1::text').getall()
        if title:
            article = {
                "link": response.url,
                "title": title,
            }
            self.articles.append(article)

    def parse_article(self, response):
        """
            This function takes the response object of the news article page and extracts the necessary information
            using get_article_data() function and constructs a dictionary using set_article_dict() function
            :param response: scrapy.http.Response object
            :return: None
        """
        
        article_data = get_article_data(response)
        article = set_article_dict(response, article_data)

        self.articles.append(article)
        
    def closed(self, reason):
        """
            This function is executed when the spider is closed. It saves the data scraped
            by the spider into a JSON file with a filename based on the spider type and
            the current date and time.
            :param reason: the reason for the spider's closure
            """
        if self.type == "sitemap":
            if not os.path.isdir('Links'):
                os.makedirs('Links')
            filename = os.path.join(
                'Links', f'le_parisien-sitemap-\
                    {datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
                )
        elif self.type == "article":
            if not os.path.isdir('Article'):
                os.makedirs('Article')
            filename = os.path.join(
                'Article', f'le_parisien-articles-\
                    {datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
                )
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
