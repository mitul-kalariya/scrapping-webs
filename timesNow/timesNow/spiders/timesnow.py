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

        initial_url = "https://www.timesnownews.com/staticsitemap/timesnow/sitemap-index.xml"
        if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
            self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
            if (self.end_date - self.start_date).days > 30:
                raise ValueError("Enter start_date and end_date for maximum 30 days.")
            else:
                self.start_urls.append(initial_url)

        elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
            today_time = datetime.today().strftime("%Y-%m-%d")
            self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
            self.start_urls.append(initial_url)

        elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:
            raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

        elif self.type == "articles" and self.url is not None:
            self.start_urls.append(self.url)

        elif self.type == "articles" and self.url is None:
            raise ValueError("type articles must be used with url")

        else:
            raise ValueError("type should be articles or sitemap")

    def parse(self, response):
        if self.type == "sitemap":
            mod_date = Selector(response, type='xml').xpath('//sitemap:lastmod/text()',
                                                            namespaces=self.namespace).getall()
            site_map_url = Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                namespaces=self.namespace).getall()

            # if not today's date the start date and end date will be available
            if not self.today_date:
                for url, date in zip(site_map_url, mod_date):
                    _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                    if _date.month == self.start_date.month or _date.month == self.end_date.month:
                        yield response.follow(url, callback=self.parse_sitemap)

            # else it will fetch only today's date as start date and date is none
            else:
                try:
                    for url, date in zip(site_map_url, mod_date):
                        _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                        if _date.month == self.today_date.month:
                            yield response.follow(url, callback=self.parse_sitemap)
                except Exception as e:
                    self.logger.exception(f"Error in parse():- {e}")

        if self.type == "articles":
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
        title = response.css('._1FcxJ::text').get()
        if title:
            article = {
                "link": response.url,
                "title": title,
            }
            self.articles.append(article)

    def parse_article(self, response):
        title = response.css('#readtrinity0  h1._1FcxJ::text').getall()
        sub_title = response.css('#readtrinity0 div.QA-An h2::text').get()
        img_url = response.css('#readtrinity0 div._3lDdd img::attr(src)').get()
        img_caption = response.css('#readtrinity0 div._3NUGP div.trinity-skip-it p::text').get()
        text = response.css('#readtrinity0 div._18840::text').getall()
        category = response.css('#readtrinity0 div.Faqqe li a p::text').getall()
        tags = response.css('#readtrinity0 div.regular a div::text').getall()
        selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        string = selector[2]
        json_data = json.loads(string)
        json_ld_blocks = []
        for block in selector:
            json_ld_blocks.append(json.loads(block))

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
                    "alternativeHeadline": sub_title,
                    "dateModified": json_data['dateModified'],
                    "datePublished": json_data['datePublished'],
                    "description": json_data['description'],
                    "author": json_data['author'],
                    "publisher": {'@type': json_data['publisher']['@type'],
                                  'name': json_data['publisher']['name'],
                                  'logo': {'@type': json_data['publisher']['logo']['@type'],
                                           'url': json_data['publisher']['logo']['url'],
                                           'width': {'@type': "Distance",
                                                     "name": str(json_data['publisher']['logo']['width']) + " Px"},
                                           'height': {'@type': "Distance",
                                                     'name': str(json_data['publisher']['logo']['height']) + " Px"}}},
                    "image": {
                        "@type": "ImageObject",
                        "url": img_url,
                        "caption": img_caption
                    }

                },
                "misc":   json_ld_blocks
            },
            "parsed_data": {
                "author": json_data['author'],
                "description": sub_title,
                "modified_at": json_data['dateModified'],
                "published_at": json_data['datePublished'],
                "retrieved_at": [datetime.today().strftime("%Y-%m-%d")],
                "publisher": json_data['publisher'],
                "text": text,
                "thumbnail_image": [img_url],  # need to look it
                "title": title,
                "images": {'image_url': img_url, 'image_caption': img_caption},
                # "video": {"link": video_link, "caption": None},
                "section": "".join(category).split(","),
                "tags": tags
            }
        }
        self.articles.append(article)

    def closed(self, reason):
        if self.type == "sitemap":
            filename = f'timesnow-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        elif self.type == "articles":
            filename = f'timesnow-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
