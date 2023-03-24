# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.utils.python import to_bytes

from six.moves.queue import Queue
from six.moves.urllib.parse import urlparse

import base64
import random

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter

class ProxyRotatorMiddleware(object):

    def __init__(self, settings):
        self.settings = settings
        self.proxies = Queue()
        self.proxy_auth = {}
        self.max_failed = 3
        self.failed = {}

        for proxy in settings.get('ROTATING_PROXY_LIST', []):
            parsed = urlparse(proxy)
            if parsed.scheme == 'http':
                self.proxies.put('http://' + proxy)
            elif parsed.scheme == 'https':
                self.proxies.put('https://' + proxy)
            else:
                raise NotConfigured('Unsupported proxy scheme %s' % proxy)

            if parsed.username and parsed.password:
                self.proxy_auth[proxy] = 'Basic ' + base64.b64encode(
                    to_bytes(parsed.username + ':' + parsed.password)).decode('ascii')

        if len(self.proxies) == 0:
            raise NotConfigured('Empty ROTATING_PROXY_LIST')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        if 'proxy' in request.meta:
            if request.meta['proxy'] in self.failed and self.failed[request.meta['proxy']] >= self.max_failed:
                del request.meta['proxy']
            else:
                return
        if self.proxies.qsize() == 0:
            raise ValueError('All proxies are unusable, cannot proceed')
        request.meta['proxy'] = self.proxies.get()
        if request.meta['proxy'] in self.proxy_auth:
            request.headers['Proxy-Authorization'] = self.proxy_auth[request.meta['proxy']]

    def process_response(self, request, response, spider):
        if response.status in [503, 500, 502, 504, 400, 408]:
            proxy = request.meta['proxy']
            if proxy not in self.failed:
                self.failed[proxy] = 0
            self.failed[proxy] += 1
            spider.logger.warning(f'{proxy} returned {response.status}.')
            return request.copy()

        proxy = request.meta.get('proxy')
        if proxy and proxy in self.failed:
            del self.failed[proxy]

        return response

    def process_exception(self, request, exception, spider):
        proxy = request.meta.get('proxy')
        if proxy not in self.failed:
            self.failed[proxy] = 0
        self.failed[proxy] += 1
        spider.logger.warning(f'Proxy {proxy} failed with exception: {exception}.')
        return request.copy()


class NewtonScrappingSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class NewtonScrappingDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)






