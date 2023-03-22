import os
from .utils import check_cmd_args, get_article_data, set_article_dict
import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector


class CP24News(scrapy.Spider):
    name = "cp24"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(CP24News, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.url = url
        self.today_date = None
        self.start_date = start_date
        self.end_date = end_date

        check_cmd_args(self, self.start_date, self.end_date)

    def parse(self, response):
        """
               Parses the given `response` object and extracts sitemap URLs or sends a
               request for articles based on the `type` attribute of the class instance.
               If `type` is "sitemap", extracts sitemap URLs from the XML content of the
               response and sends a request for each of them to Scrapy's engine with the
               callback function `parse_sitemap`.
               If `type` is "articles", sends a request for the given URL to Scrapy's engine
               with the callback function `parse_article`.
               This function is intended to be used as a Scrapy spider callback function.
               :param response: A Scrapy HTTP response object containing sitemap or article content.
               :return: A generator of Scrapy Request objects, one for each sitemap
               or article URL found in the response.
        """
        if self.type == "sitemap":
            for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                     namespaces=self.namespace).getall()[1:3]:
                yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        elif self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
        """
        This function parses the sitemap page and extracts the URLs of individual articles.
        :param response: the response object of the sitemap page
        :return: a scrapy.Request object for each individual article URL
        """
        self.logger.info('---------- Calling parse sitemap article for each article url ------------')
        for article_url in response.css('div.listInnerHorizontal  h2.teaserTitle a::attr("href")').getall():
            yield scrapy.Request(article_url, callback=self.parse_sitemap_article)

    def parse_sitemap_article(self, response):
        """
         This function parses the sitemap page and extracts the URLs of individual articles.

         :param response: the response object of the sitemap page
         :type response: scrapy.http.Response

         :return: a scrapy.Request object for each individual article URL
         :rtype: scrapy.Request
         """
        selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        string = selector[0].split('"datePublished":')
        published_date = string[1].split('"')[1].strip()
        published_date = datetime.strptime(published_date[:10], '%Y-%m-%d')
        if self.start_date is None and self.end_date is None:

            if published_date == self.today_date:

                title = response.css('h1.articleHeadline::text').get()
                if title:
                    article = {
                        "link": response.url,
                        "title": title,
                    }
                    self.logger.info("---------- Fetching today's sitemap data ------------")
                    self.articles.append(article)
            else:
                self.logger.info(">>>>> There's no article url and link for Today's Date")

        elif self.start_date <= published_date <= self.end_date:
            title = response.css('h1.articleHeadline::text').get()
            if title:
                article = {
                    "link": response.url,
                    "title": title,
                }
                self.logger.info('---------- Fetching sitemap data for given range  ------------')
                self.articles.append(article)
        else:
            self.logger.info(">>>>>>> There's no article url and link for given date of range")

    def parse_article(self, response):
        """
        This function takes the response object of the news article page and extracts the necessary information
        using get_article_data() function and constructs a dictionary using set_article_dict() function
        :param response: scrapy.http.Response object
        :return: None
        """
        self.logger.info('---------- Fetching article data for given url ------------')
        article_data = get_article_data(self, response)
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
                'Links', f'{self.name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
            )
        elif self.type == "article":
            if not os.path.isdir('Article'):
                os.makedirs('Article')
            filename = os.path.join(
                'Article', f'{self.name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
            )
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
