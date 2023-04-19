from scrapy.crawler import CrawlerProcess
from multiprocessing import Process, Queue

from crwstern.spiders.stern import SternSpider
from crwstern import exceptions


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
        self.output_queue = None
        self.query = query
        self.proxies = proxies

    def crawl(self) -> list[dict]:
        self.output_queue = Queue()
        process = Process(
            target=self.start_crawler, args=(self.query, self.output_queue)
        )
        process.start()

        articles = self.output_queue.get()

        if articles == "Error in Proxy Configuration":
            raise exceptions.ProxyConnectionException("Error in Proxy Configuration")

        return articles

    def start_crawler(self, query, output_queue):
        """Crawls the sitemap URL and article URL and return final data

        Raises:
            Exception: Raised exception for unknown Type

        Returns:
            list[dict]: list of dictionary of the article data or article links
            as per expected_article.json or expected_sitemap.json
        """

        process = CrawlerProcess()
        process_settings = process.settings
        process_settings["DOWNLOADER_MIDDLEWARES"]["crwstern.middlewares.CustomProxyMiddleware"] = 110
        process_settings["DOWNLOAD_DELAY"] = 0.25
        process_settings["REFERER_ENABLED"] = False
        process_settings["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"  # noqa: E501
        process.settings = process_settings
        if self.query["type"] == "article":
            spider_args = {
                "type": "article",
                "url": self.query.get("link"),
                "args": {"callback": output_queue.put},
            }
        elif self.query["type"] == "sitemap":
            spider_args = {"type": "sitemap", "args": {"callback": output_queue.put}}
        else:
            raise Exception("Invalid Type")

        spider_args["args"]["proxies"] = self.proxies

        process.crawl(SternSpider, **spider_args)
        process.start()
