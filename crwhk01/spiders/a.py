import scrapy

class HK01SitemapSpider(scrapy.Spider):
    name = 'aaa'
    allowed_domains = ['www.hk01.com']
    start_urls = ['https://www.hk01.com/sitemap.xml']
    namespaces = {'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    def parse(self, response):
        for url in response.xpath('//xmlns:url', namespaces=self.namespaces):
            link = url.xpath('xmlns:loc/text()', namespaces=self.namespaces).get()
            yield scrapy.Request(link, self.parse_sitemap)

    def parse_sitemap(self, response):
        link = response.url
        title = response.css('#articleTitle::text').get()
        published_at = response.css('.inline time::attr(datetime)').get()



        if link and title and published_at:
            published_at = published_at[:10]
            yield {
                'link': link,
                'title': title,
                'date': published_at
            }

