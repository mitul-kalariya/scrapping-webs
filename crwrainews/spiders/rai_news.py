import scrapy


class RaiNewsSpider(scrapy.Spider):
    name = "rai_news"
    allowed_domains = ["rai_news.com"]
    start_urls = ["http://rai_news.com/"]

    def parse(self, response):
        pass
