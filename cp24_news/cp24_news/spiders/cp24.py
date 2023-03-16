import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings


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

        initial_url = "https://www.cp24.com/sitemap.xml"
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
                                                                     namespaces=self.namespace).getall()[1:3]:
                yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        elif self.type == "article":
            yield scrapy.Request(self.url, callback=self.parse_article)

    def parse_sitemap(self, response):
        self.logger.info('---------- Calling parse sitemap article for each article url ------------')
        for article_url in response.css('div.listInnerHorizontal  h2.teaserTitle a::attr("href")').getall():
            yield scrapy.Request(article_url, callback=self.parse_sitemap_article)

    def parse_sitemap_article(self, response):

        selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        string = selector[0].split('"datePublished":')
        published_date = string[1].split('"')[1].strip()
        # json_data = json.loads(string)
        # published_date = json_data['datePublished']
        published_date = datetime.strptime(published_date[:10], '%Y-%m-%d')
        if self.start_date == None and self.end_date == None:

            if published_date == self.today_date:

                title = response.css('h1.articleHeadline::text').get()
                if title:
                    article = {
                        "link": response.url,
                        "title": title,
                    }
                    self.logger.info("---------- Fetching today's sitemap data ------------")
                    self.articles.append(article)

        elif self.start_date <= published_date <= self.end_date:
            title = response.css('h1.articleHeadline::text').get()
            if title:
                article = {
                    "link": response.url,
                    "title": title,
                }
                self.logger.info('---------- Fetching sitemap data for given range  ------------')
                self.articles.append(article)

    def parse_article(self, response):
        self.logger.info('---------- Fetching article data for given url ------------')
        title = response.css('h1.articleHeadline::text').get()
        img_url = response.css('div.article div.image img::attr(src)').get()
        img_caption = response.css('div.article div.image p::text').get()
        article_body_img = response.css('div.articleBody p img::attr(src)').getall()
        author_url = response.css('div.prof a::attr("href")').get()
        text = " ".join(response.css('div.articleBody > p::text').getall())
        section_meta = response.xpath('//meta[@property="article:section"]')
        section_content = section_meta.xpath('@content').get()
        selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()

        json_ld_blocks = []
        for sec in selector:
            json_ld_blocks.append(json.loads(sec))

        article_img = [{"link": article, "caption": None} for article in article_body_img]

        string = selector[0]
        json_data = json.loads(string)

        try:
            modified_date = json_data['dateModified']
        except:
            modified_date = None
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
                    # "alternativeHeadline": sub_title,
                    "dateModified": modified_date,
                    "datePublished": json_data['datePublished'],
                    "description": json_data['description'],
                    "author": {'@type': json_data['author'][0]["@type"], 'name': json_data['author'][0]['name'],
                               'url': author_url},
                    "publisher": {
                        '@id': json_ld_blocks[1]['url'],
                        '@type': json_data['publisher']['@type'],
                        'name': json_data['publisher']['name'],
                        'logo': {
                            '@type': json_data['publisher']['logo']['@type'],
                            'url': json_data['publisher']['logo']['url'],
                            'width': {
                                '@type': "Distance",
                                "name": str(json_data['publisher']['logo']['width']) + " Px"},
                            'heigt': {
                                '@type': "Distance",
                                'name': str(json_data['publisher']['logo']['height']) + " Px"}}},
                    "image": {
                        "@type": "ImageObject",
                        "url": img_url,
                    }

                },
                "misc": json_ld_blocks
            },
            "parsed_data": {
                "author": {'@type': json_data['author'][0]["@type"], 'name': json_data['author'][0]['name'],
                           'url': author_url},
                "description": [json_data['description']],
                "published_at": [json_data['datePublished']],
                "publisher": [{'@id': json_ld_blocks[1]['url'], '@type': json_data['publisher']['@type'],
                              'name': json_data['publisher']['name'],
                              'logo': {'@type': json_data['publisher']['logo']['@type'],
                                       'url': json_data['publisher']['logo']['url'], 'width': {'@type': "Distance",
                                                                                               "name": str(json_data[
                                                                                                               'publisher'][
                                                                                                               'logo'][
                                                                                                               'width']) + " Px"},
                                       'heigt': {'@type': "Distance",
                                                 'name': str(json_data['publisher']['logo']['height']) + " Px"}}}],
                "text": [text],
                "thumbnail_image": [img_url],  # need to look it
                "title": [title],
                "images": [{'link': img_url, 'caption': img_caption}] + article_img,
                "section": "".join(section_content).split(",")
            }
        }

        self.articles.append(article)

    def closed(self, reason):
        if self.type == "sitemap":
            filename = f'cp24news-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        elif self.type == "article":
            filename = f'cp24news-article-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
        self.logger.info(f'---------- stored the following data {filename}------------')

