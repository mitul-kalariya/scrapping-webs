from scrapy.crawler import CrawlerProcess
from crwmetropoles.spiders.metropoles import MetropolesSpider


class Crawler:
    """
    A class used to crawl the sitemap and article data.
    ...

    Attributes
    ----------
    query : dict
        query dictionary that contains type, link, domain, since and until
    proxies : str
        dictionary that contains proxy related information
    output : int
        Data returned by crawl method

    Methods
    -------
    crawl()
        Crawls the sitemap URL and article URL and return final data
    def yield_output(data)
        set data to output attribute
    """

    def __init__(self, query={'type': None}, proxies={}):
        """
        Args:
            query (dict): A dict that takes input for crawling the link for one of the below type.\n
            for sitemap:- {
                "type": "sitemap", "domain": "https://example.com",\n
                "since": "2022-03-01", "until": "2022-03-26"\n
                }
            for article:- {"type": "article", "link": https://example.com/articles/test.html"}\n
            for link_feed:- {"type": "link_feed"}. Defaults to {'type': None}.\n
            proxies (dict, optional): Use:- {
                "proxyIp": "123.456.789.2", "proxyPort": "3199",\n
                "proxyUsername": "IgNyTnddr5", "proxyPassword": "123466"\n
                }. Defaults to {}.
        """
        self.output = None
        self.query = query
        self.proxies = proxies

    def crawl(self) -> list[dict]:
        """Crawls the sitemap URL and article URL and return final data

        Raises:
            Exception: Raised exception for unknown Type

        Returns:
            list[dict]: list of dictionary of the article data or article links
            as per expected_article.json or expected_sitemap.json
        """
        self.output = None
        process = CrawlerProcess()
        if self.query['type'] == 'article':
            spider_args = {'type': 'article', 'url': self.query.get('link'), 'args': {'callback': self.yield_output}}
        elif self.query['type'] == 'sitemap' or self.query['type'] == 'link_feed':
            spider_args = {'type': 'sitemap', 'args': {'callback': self.yield_output}}
            if self.query.get('since') and self.query.get('until'):
                spider_args['start_date'] = self.query['since']
                spider_args['end_date'] = self.query['until']
            process_settings = process.settings
            process_settings["DOWNLOAD_DELAY"] = 0.25
            process_settings["REFERER_ENABLED"] = False
            process_settings["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"  # noqa: E501
            process.settings = process_settings
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

        process.crawl(MetropolesSpider, **spider_args)
        process.start()
        return self.output

    def yield_output(self, data):
        self.output = data
