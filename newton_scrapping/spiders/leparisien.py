import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings


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

        initial_url = "https://www.leparisien.fr/arc/outboundfeeds/news-sitemap-index/?from=0&outputType=xml&_website" \
                      "=leparisien"
        if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
            self.logger.info('---------- Entering to fetch data for sitemap when start_date and end_date is given '
                             '------------')
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
            self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
            if (self.end_date - self.start_date).days > 30:
                raise ValueError("Enter start_date and end_date for maximum 30 days.")
            else:
                self.start_urls.append(initial_url)

        elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
            self.logger.info('---------- Entering to fetch data for sitemap when start_date and end_date is not given '
                             '------------')
            today_time = datetime.today().strftime("%Y-%m-%d")
            self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
            self.start_urls.append(initial_url)

        elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:
            raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

        elif self.type == "article" and self.url is not None:
            self.logger.info('---------- Entering to fetch article data for given url ------------')
            self.start_urls.append(self.url)

        elif self.type == "article" and self.url is None:
            raise ValueError("type article must be used with url")

        else:
            raise ValueError("type should be article or sitemap")

    def parse(self, response):
        if self.type == "sitemap":
            for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()',
                                                                     namespaces=self.namespace).getall():
                yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        elif self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):

        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        published_date = Selector(response, type='xml').xpath('//news:publication_date/text()',
                                                              namespaces=self.namespace).getall()
        title = Selector(response, type='xml').xpath('//news:title/text()', namespaces=self.namespace).getall()
        if self.start_date is not None and self.end_date is not None:
            for article, date, title in zip(article_urls, published_date, title):
                if self.start_date <= datetime.strptime(date.split('T')[0], '%Y-%m-%d') <= self.end_date:
                    self.logger.info('---------- Fetching sitemap data for given date range  ------------')
                    article = {
                        "link": article,
                        "title": title,
                    }
                    self.articles.append(article)


        elif self.start_date is None and self.end_date is None:
            for article, date, title in zip(article_urls, published_date, title):
                _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
                if _date == self.today_date:
                    self.logger.info("---------- Fetching today's sitemap data ------------")
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
        title = response.css('#top > header > h1::text').getall()
        if title:
            article = {
                "link": response.url,
                "title": title,
            }
            self.articles.append(article)

    def parse_article(self, response):
        self.logger.info('---------- Fetching article data for given url ------------')
        title = response.css('header.article_header > h1::text').getall()
        img_url = response.css("div.width_full >figure > div.pos_rel > img::attr('src')").getall()
        img_caption = response.css('div.width_full >figure > figcaption > span::text').getall()
        article_author_url = response.css('a.author_link::attr(href)').getall()
        video_link = response.css('iframe.dailymotion-player::attr(src)').getall()
        text = response.css('section.content > p::text').getall()
        category = response.css('div.breadcrumb > a::text').getall()

        json_data = "".join(response.css('script[type="application/ld+json"]::text').getall())

        json_data = json.loads(json_data)

        article = {
            'raw_response': {
                "content_type": response.headers.get("Content-Type").decode("utf-8"),
                "content": response.text,
            },
            "parsed_json": {
                "main": {
                    "@context": json_data[1]["@context"],
                    "@type": json_data[1]["@type"],
                    "mainEntityOfPage": {
                        "@type": json_data[1]["mainEntityOfPage"]["@type"],
                        "@id": json_data[1]["mainEntityOfPage"]["@id"]
                    },
                    "headline": json_data[1]['headline'],
                    "alternativeHeadline": json_data[1]['alternativeHeadline'],
                    "dateModified": json_data[1]['dateModified'],
                    "datePublished": json_data[1]['datePublished'],
                    "description": json_data[1]['description'],
                    "author":
                        {
                            "@type": json_data[1]['author'][0]["@type"],
                            "name": json_data[1]['author'][0]["name"],

                        }
                    ,

                    "publisher": {'@type': json_data[1]['publisher']['@type'],
                                  "@id": json_data[2]["url"],
                                  'name': json_data[1]['publisher']['name'],
                                  'logo': {'@type': json_data[1]['publisher']['logo']['@type'],
                                           'url': json_data[1]['publisher']['logo']['url'],
                                           'width': {'@type': "Distance",
                                                     "name": str(json_data[1]['publisher']['logo']['width']) + " Px"},
                                           'height': {'@type': "Distance", 'name': str(
                                               json_data[1]['publisher']['logo']['height']) + " Px"}}},

                    "image": json_data[1]["image"],

                },
                "misc": json_data
            },

            "parsed_data": {
                "author": [
                    {
                        "@type": json_data[1]['author'][0]["@type"],
                        "name": json_data[1]['author'][0]["name"],
                    }
                ],
                "description": [json_data[1]['description']],
                "modified_at": [json_data[1]['dateModified']],
                "published_at": [json_data[1]['datePublished']],

                "publisher": [{'@type': json_data[1]['publisher']['@type'],
                               'name': json_data[1]['publisher']['name'],
                               'logo': {'@type': json_data[1]['publisher']['logo']['@type'],
                                        'url': json_data[1]['publisher']['logo']['url'], 'width': {'@type': "Distance",
                                                                                                   "name": str(
                                                                                                       json_data[1][
                                                                                                           'publisher'][
                                                                                                           'logo'][
                                                                                                           'width']) + "Px"},
                                        'height': {'@type': "Distance",
                                                   'name': str(json_data[1]['publisher']['logo']['height']) + " Px"}}}],

                "text": text,
                "thumbnail_image": [json_data[2]["url"] + img_url[0][1:]],  # need to look it
                "title": title,
                "images": [{'link': json_data[2]["url"] + img_url[0][1:], 'caption': img_caption[0]}],

                "section": "".join(category).split(","),
                "tag": json_data[1]["keywords"]
            }
        }
        if article_author_url:
            article['parsed_json']['main']['author']['url'] = json_data[2]["url"] + article_author_url[0][1:]
            article['parsed_data']['author'][0]['url'] = json_data[2]["url"] + article_author_url[0][1:]

        if video_link:
            article['parsed_data']['embed_video_link'] = [video_link]
        self.articles.append(article)

        try:
            article['parse_json']['main']['isPartOf'] = json_data[1]["isPartOf"]
            article['parse_json']['main']["isAccessibleForFree"] = json_data[1]["isAccessibleForFree"]
        except:
            pass

    def closed(self, reason):
        if self.type == "sitemap":
            filename = f'leparisien-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        elif self.type == "article":
            filename = f'leparisien-article-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
