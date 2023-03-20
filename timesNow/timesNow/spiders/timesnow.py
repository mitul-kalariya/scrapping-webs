import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector

from scrapy.utils.project import get_project_settings


class TimesNow(scrapy.Spider):
    name = "times_now_news"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(TimesNow, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.url = url
        self.start_date = start_date  # datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = end_date  # datetime.strptime(end_date, '%Y-%m-%d')
        self.today_date = None
        from .utility import check_cmd_args
        check_cmd_args(self, self.start_date, self.end_date)

    def parse(self, response):
        """
        Parses the given `response` object and extracts sitemap URLs or sends a request for articles based on the `type` attribute of the class instance.
        If `type` is "sitemap", extracts sitemap URLs from the XML content of the response and sends a request for each of them to Scrapy's engine with the callback function `parse_sitemap`.
        If `type` is "articles", sends a request for the given URL to Scrapy's engine with the callback function `parse_article`.
        This function is intended to be used as a Scrapy spider callback function.
        :param response: A Scrapy HTTP response object containing sitemap or article content.
        :return: A generator of Scrapy Request objects, one for each sitemap or article URL found in the response.
        """
        if self.type == "sitemap":
            # mod_date = Selector(response, type='xml').xpath('//sitemap:lastmod/text()',
            #                                                 namespaces=self.namespace).getall()
            site_map_url = Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                namespaces=self.namespace).getall()
            for url in site_map_url:
                yield response.follow(url, callback=self.parse_sitemap)
        elif self.type == "articles":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        mod_date = Selector(response, type='xml').xpath('//sitemap:lastmod/text()', namespaces=self.namespace).getall()
        try:
            for url, date in zip(article_urls, mod_date):
                _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                if self.today_date:
                    if _date == self.today_date:
                        yield scrapy.Request(url, callback=self.parse_sitemap_article)
                else:
                    if self.start_date <= _date <= self.end_date:
                        yield from scrapy.Request(url, callback=self.parse_sitemap_article)
        except Exception as e:
            self.logger.exception(f"Error in parse_sitemap:- {e}")

    def parse_sitemap_article(self, response):
        title = response.css('._1FcxJ::text').get()
        if title:
            article = {
                "link": response.url,
                "title": title,
            }
            self.articles.append(article)

    def parse_article(self, response):
        from .utility import get_article_data
        article_data = get_article_data(response)

        from .utility import set_article_dict
        article = set_article_dict(response, article_data)
        self.articles.append(article)

    def closed(self, reason):
        if self.type == "sitemap":
            filename = f'timesnow-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        elif self.type == "articles":
            filename = f'timesnow-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
