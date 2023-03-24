import scrapy
import json
import os
from datetime import datetime
from scrapy.selector import Selector
from .utils import check_cmd_args, get_article_data, set_article_dict


class FranceTvInfo(scrapy.Spider):
    name = "francetv-info"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(FranceTvInfo, self).__init__(*args, **kwargs)
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
        This function is used to parse the response from a web page or a sitemap.

        Args:
            self: The spider object that calls this function.
            response: The response object returned by a web page or a sitemap.

        Returns:
            If the response is from a sitemap and contains article URLs within the desired time range
            (specified by the spider object's `start_date`, `end_date`, or `today_date` attributes),
            this function yields a request object for each article URL using the `parse_sitemap` callback.
            If the response is from an article URL, this function yields a request object for the article
            using the `parse_article` callback.
        """
        if self.type == "sitemap":

            for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                     namespaces=self.namespace).getall():

                if "article" in site_map_url:
                    sitemap_moth = site_map_url.split('-')[1]
                    sitemap_year = site_map_url.split('-')[0][-4:]
                    sitemap_date = datetime.strptime(f'{sitemap_year}-{sitemap_moth}', '%Y-%m')
                    if not self.today_date:
                        _start_date = self.start_date.strftime('%Y-%m')
                        _end_date = self.end_date.strftime('%Y-%m')
                        _start_date = datetime.strptime(_start_date, '%Y-%m')
                        _end_date = datetime.strptime(_end_date, '%Y-%m')
                        if _start_date <= sitemap_date <= _end_date:
                            yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
                    else:
                        _today_date = self.today_date.strftime('%Y-%m')
                        _today_date = datetime.strptime(_today_date, '%Y-%m')
                        if _today_date == sitemap_date:
                            yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        if self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
        """
           Parses the sitemap and extracts the article URLs and their last modified date.
           If the last modified date is within the specified date range, sends a request to the article URL
           :param response: the response from the sitemap request
           :return: scrapy.Request object
           """

        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        sitemap_articel_urls = []
        mod_date = Selector(response, type='xml').xpath('//sitemap:lastmod/text()', namespaces=self.namespace).getall()
        if self.today_date:
            try:
                for url, date in zip(article_urls, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if _date == self.today_date:
                        yield scrapy.Request(url, callback=self.parse_sitemap_article)
            except Exception as e:
                self.logger.exception(f"Error in parse_sitemap:- {e}")
        else:
            try:
                for url, date in zip(article_urls, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if self.start_date <= _date <= self.end_date:
                        sitemap_articel_urls.append(url)
                yield from response.follow_all(sitemap_articel_urls, callback=self.parse_sitemap_article)
            except Exception as e:
                self.logger.exception(f"Error in parse_sitemap:- {e}")

    def parse_sitemap_article(self, response):
        """
        Parse article information from a given sitemap URL.

        :param response: HTTP response from the sitemap URL.
        :return: None
        """
        title = response.css('h1.c-title ::text').get()
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
        article = set_article_dict(self, response, article_data)

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
                'Links', f'france-tv-info-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
            )
        elif self.type == "article":
            if not os.path.isdir('Article'):
                os.makedirs('Article')
            filename = os.path.join(
                'Article', f'france-tv-info-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
            )
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
