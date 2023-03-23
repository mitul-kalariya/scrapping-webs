import os

import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector
from .utils import check_cmd_args, set_article_dict, get_article_data


class NewsTVB(scrapy.Spider):
    name = "tvb"
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(
        self, type=None, start_date=None,
        end_date=None, url=None, *args, **kwargs
                ):
        super(NewsTVB, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.url = url
        self.start_date = start_date  # datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = end_date  # datetime.strptime(end_date, '%Y-%m-%d')
        self.today_date = None
        
        check_cmd_args(self, self.start_date, self.end_date)

    def parse(self, response):
        """
        Parses the given `response` object and extracts sitemap URLs or sends a
        request for articles based on the `type` attribute of the class instance.
        If `type` is "sitemap", extracts sitemap URLs from the XML content of the response and sends a request for each of them to Scrapy's engine with the callback function `parse_sitemap`.
        If `type` is "articles", sends a request for the given URL to Scrapy's engine with the callback function `parse_article`.
        This function is intended to be used as a Scrapy spider callback function.
        :param response: A Scrapy HTTP response object containing sitemap or article content.
        :return: A generator of Scrapy Request objects, one for each sitemap or article URL found in the response.
        """
        if self.type == "sitemap":
            article_url = Selector(response, type='xml')\
                .xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
            article_title = Selector(response, type='xml')\
                .xpath('//news:title/text()', namespaces=self.namespace).getall()
            print(article_title, article_url)
            for url, title in zip(article_url, article_title):
                article = {
                    "link": url,
                    "title": title
                }
                self.articles.append(article)
                # yield scrapy.Request(url, callback=self.parse_sitemap_article)

        elif self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
        """
           Parses the sitemap and extracts the article URLs and their last modified date.
           If the last modified date is within the specified date range, sends a request to the article URL
           :param response: the response from the sitemap request
           :return: scrapy.Request object
           """
        article_urls = response.css("div.BigNewsContainer a::attr('href')").getall()
        print(article_urls)
        try:
            for url in article_urls:
                url = f"https://news.tvb.com{url}"
                yield scrapy.Request(
                    url, callback=self.parse_sitemap_article)
        except Exception as e:
            self.logger.exception(f"Error in parse_sitemap:- {e}")

    def parse_sitemap_article(self, response):
        """
           Parse article information from a given sitemap URL.

           :param response: HTTP response from the sitemap URL.
           :return: None
        """
        # Extract the article title from the response
        title = response.css('div.newsEntryContainer h1::text').get()
        # If the title exists, add the article information to the list of articles
        if title:
            article = {
                "link": response.url,
                "title": title
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
                'Links', f'news-tvb-sitemap-\
                    {datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
                )
        elif self.type == "article":
            if not os.path.isdir('Article'):
                os.makedirs('Article')
            filename = os.path.join(
                'Article', f'news-tvb-articles-\
                    {datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
                )
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
