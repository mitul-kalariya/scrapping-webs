"""exceptions.py file"""


class InvalidArgumentException(Exception):
    pass


class InputMissingException(Exception):
    pass


class SitemapScrappingException(Exception):
    pass


class SitemapArticleScrappingException(Exception):
    pass


class ArticleScrappingException(Exception):
    pass


class ProxyConnectionException(Exception):
    pass


class CrawlerClosingException(Exception):
    pass
