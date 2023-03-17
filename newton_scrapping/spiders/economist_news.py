import os

import scrapy
import json
import re
from datetime import datetime, timedelta
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings


class Economist(scrapy.Spider):
    name = "economist_canada"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                 'news': "http://www.google.com/schemas/sitemap-news/0.9"}

    def __init__(self, type=None, start_date=None, end_date=None, url=None, *args, **kwargs):
        super(Economist, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.url = url
        self.start_date = start_date  # datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = end_date  # datetime.strptime(end_date, '%Y-%m-%d')
        self.today_date = None

        initial_url = "https://www.economist.com/sitemap.xml"
        if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
            self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
            if (self.end_date - self.start_date).days > 30:
                raise ValueError("Enter start_date and end_date for maximum 30 days.")
            else:
                self.start_urls.append(initial_url)

        elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
            # today_time = datetime.today().strftime("%Y-%m-%d")
            # self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
            self.today_date = datetime(2023, 3, 16)

            self.start_urls.append(initial_url)

        elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:

            raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

        elif self.type == "article" and self.url is not None:
            self.start_urls.append(self.url)

        elif self.type == "article" and self.url is None:
            raise ValueError("type article must be used with url")

        else:
            raise ValueError("type should be articles or sitemap")

    def parse(self, response):
        if self.type == "sitemap":
            # if not self.today_date:
            for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                     namespaces=self.namespace).getall()[4:]:
                # year, quarter = re.findall(r'(\d{4})-Q(\d)', site_map_url)[0]
                # year = int(year)
                # quarter = int(quarter)
                #
                # # Calculate the start of the quarter
                # quarter_start = datetime(year, 3 * quarter - 2, 1)
                #
                # """Calculate the end of the quarter by adding 3 months to the start of the quarter and
                # subtracting 1 day"""
                # quarter_end = quarter_start.replace(month=quarter_start.month + 3, day=1) - timedelta(days=1)
                # # print(quarter_end)
                # # print(quarter_start)
                #
                # # Check if the URL falls within the given date range
                # if self.start_date <= quarter_end and self.end_date >= quarter_start:
                yield scrapy.Request(site_map_url, callback=self.parse_sitemap)
            # else:
            #     for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
            #                                                              namespaces=self.namespace).getall()[4:]:
            #         year, quarter = re.findall(r'(\d{4})-Q(\d)', site_map_url)[0]
            #         year = int(year)
            #         quarter = int(quarter)
            #
            #         # Calculate the start of the quarter
            #         quarter_start = datetime(year, 3 * quarter - 2, 1)
            #
            #         """Calculate the end of the quarter by adding 3 months to the start of the quarter and
            #         subtracting 1 day"""
            #         print(f'-----------------------{quarter_start.month+3}-----------------------------------')
            #         quarter_end = quarter_start.replace(month=quarter_start.month + 3, day=1) - timedelta(days=1)
            #         print(quarter_end)
            #         # Check if the URL falls within the given date range
            #         if self.today_date <= quarter_end or self.today_date >= quarter_start:
            #             yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        if self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
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
        title = response.css('#content h1::text').get()
        if title:
            article = {
                "link": response.url,
                "title": title,
            }
            self.articles.append(article)

    def parse_article(self, response):

        headline = response.css('#content h1::text').get()
        alternative_headline = response.css('#content h2::text').get()

        selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        logo_height = response.css('#ds-economist-logo::attr("height")').get()
        logo_width = response.css('#ds-economist-logo::attr("width")').get()

        json_data = json.loads(selector[0])

        article = {
            'raw_response': {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            },
            "parsed_json": {
                "main": {
                    "@context": json_data['@context'],
                    "@type": json_data['@type'],
                    "mainEntityOfPage": {
                        "@type": "WebPage",
                        "@id": json_data['mainEntityOfPage']
                    },
                    "headline": json_data['headline'],
                    "alternativeHeadline": alternative_headline,
                    "dateModified": json_data['dateModified'],
                    "datePublished": json_data['datePublished'],
                    "description": json_data['description'],
                    "author": {"@type": json_data['author']['@type'], "name": json_data['author']['name'],
                               "url": json_data['author']['logo']['url']},
                    "publisher": {'@type': json_data['publisher']['@type'],
                                  'name': json_data['publisher']['name'],
                                  'logo': {'@type': json_data['publisher']['logo']['@type'],
                                           'url': json_data['publisher']['logo']['url'],
                                           'width': {'@type': "Distance",
                                                     "name": f"{logo_width} Px"},
                                           'height': {'@type': "Distance",
                                                      'name': f"{logo_height} Px"}}},
                    "image": {
                        "@type": "ImageObject",
                        "url": json_data['image'],
                    }

                },
                "misc": json_data
            },
            "parsed_data": {
                "author": [{"@type": json_data['author']['@type'], "name": json_data['author']['name'],
                            "url": json_data['author']['logo']['url']}],
                "description": [json_data['description']],
                "modified_at": [json_data['dateModified']],
                "published_at": [json_data['datePublished']],
                "publisher": [{'@type': json_data['publisher']['@type'],
                               'name': json_data['publisher']['name'],
                               'logo': {'@type': json_data['publisher']['logo']['@type'],
                                        'url': json_data['publisher']['logo']['url'],
                                        'width': {'@type': "Distance",
                                                  "name": f"{logo_width} Px"},
                                        'height': {'@type': "Distance",
                                                   'name': f"{logo_height} Px"}}}],
                "text": [json_data['articleBody']],
                "thumbnail_image": [json_data["thumbnailUrl"]],  # need to look it
                "title": [headline],
                "images": [{"link": json_data['image']}],
                "section": [json_data['articleSection']],
                "tags": json_data['keywords']
            }
        }
        self.articles.append(article)

    def closed(self, reason):
        if self.type == "sitemap":
            if not os.path.isdir('Links'):
                os.makedirs('Links')
            filename = os.path.join('Links', f'economistnews-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}')
        elif self.type == "article":
            if not os.path.isdir('Article'):
                os.makedirs('Article')
            filename = os.path.join('Links', f'economistnews-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}')
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
