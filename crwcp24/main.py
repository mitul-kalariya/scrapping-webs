from scrapy.crawler import CrawlerProcess
from crwcp24.spiders.cp24 import CP24News


class Crawler:
    def __init__(self, query={'type': None}, proxies={}):
        self.output = None
        self.query = query
        self.proxies = proxies

    def crawl(self):
        self.output = None
        process = CrawlerProcess()
        if self.query['type'] == 'article':
            spider_args = {'type': 'article', 'url': self.query.get('link'), 'args': {'callback': self.yield_output}}
        elif self.query['type'] == 'sitemap' or self.query['type'] == 'link_feed':
            spider_args = {'type': 'sitemap', 'args': {'callback': self.yield_output}}
            if self.query.get('since') and self.query.get('until'):
                spider_args['start_date'] = self.query['since']
                spider_args['end_date'] = self.query['until']
        else:
            raise Exception('Invalid Type')

        if self.proxies:
            process_settings = process.settings
            process_settings['DOWNLOADER_MIDDLEWARES'][
                'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware'] = 400
            process_settings['HTTPPROXY_ENABLED'] = True
            process_settings['HTTP_PROXY'] = self.proxies['proxyIp'] + ':' + self.proxies['proxyPort']
            process_settings['HTTP_PROXY_USER'] = self.proxies['proxyUsername']
            process_settings['HTTP_PROXY_PASS'] = self.proxies['proxyPassword']
            process.settings = process_settings

        process.crawl(CP24News, **spider_args)
        process.start()
        return self.output

    def yield_output(self, data):
        self.output = data
